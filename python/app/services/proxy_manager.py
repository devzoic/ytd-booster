"""
Proxy Manager Service - Handles local proxy forwarding for authenticated proxies.

Each profile gets a local proxy port that forwards to the upstream authenticated proxy.
This allows Chrome to connect to localhost without authentication popup.
"""

import asyncio
import base64
import socket
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass
import sys

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ProxyForwarderServer:
    """A simple HTTP proxy that forwards to an upstream authenticated proxy."""
    
    def __init__(self, local_port: int, upstream_host: str, upstream_port: int, 
                 username: str, password: str):
        self.local_port = local_port
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.username = username
        self.password = password
        self.server = None
        self.running = False
        self._thread = None
        self._loop = None
        self._tasks = set()
    
    def _get_proxy_auth_header(self) -> bytes:
        """Generate Proxy-Authorization header."""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Proxy-Authorization: Basic {encoded}\r\n".encode()
    
    async def _handle_client(self, reader: asyncio.StreamReader, 
                              writer: asyncio.StreamWriter):
        """Handle incoming client connection."""
        upstream_writer = None
        
        try:
            # Read the initial request line
            try:
                request_line = await asyncio.wait_for(reader.readline(), timeout=30)
            except asyncio.TimeoutError:
                return
            
            if not request_line:
                return
            
            # Read all headers
            headers = bytearray()
            while True:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=10)
                except asyncio.TimeoutError:
                    break
                if line == b'\r\n' or not line:
                    break
                # Skip existing proxy-auth header
                if not line.lower().startswith(b'proxy-authorization:'):
                    headers.extend(line)
            
            # Parse request
            request_str = request_line.decode('utf-8', errors='ignore')
            is_connect = request_str.upper().startswith('CONNECT')
            
            # Check if this is a relative request (direct browser access on localhost)
            parts = request_str.split()
            is_relative = False
            if len(parts) >= 2:
                path = parts[1]
                if not path.startswith('http://') and not path.startswith('https://') and not is_connect:
                    is_relative = True
            
            if is_relative:
                status_page = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    "Connection: close\r\n\r\n"
                    "<!DOCTYPE html>\n"
                    "<html>\n"
                    "<head>\n"
                    "    <title>Proxy Tunnel Status</title>\n"
                    "    <style>\n"
                    "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }\n"
                    "        .card { background: white; padding: 2rem; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: center; border: 1px solid #e2e8f0; max-width: 400px; }\n"
                    "        .icon { font-size: 3rem; color: #4f46e5; margin-bottom: 1rem; }\n"
                    "        h1 { margin: 0 0 0.5rem 0; font-size: 1.5rem; color: #0f172a; }\n"
                    "        p { color: #64748b; margin: 0 0 1.5rem 0; font-size: 0.9rem; line-height: 1.5; }\n"
                    "        .badge { background: #e0e7ff; color: #4338ca; padding: 0.35rem 1rem; border-radius: 9999px; font-weight: 700; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; }\n"
                    "    </style>\n"
                    "</head>\n"
                    "<body>\n"
                    "    <div class='card'>\n"
                    "        <div class='icon'>⚡</div>\n"
                    "        <h1>Proxy Tunnel Active</h1>\n"
                    "        <p>Your local authenticated proxy forwarder is running and healthy on this port.</p>\n"
                    "        <span class='badge'>Status: Online</span>\n"
                    "    </div>\n"
                    "</body>\n"
                    "</html>\n"
                )
                writer.write(status_page.encode())
                await writer.drain()
                return

            # Read all headers
            headers = bytearray()
            connection_header_found = False
            while True:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=10)
                except asyncio.TimeoutError:
                    break
                if line == b'\r\n' or not line:
                    break
                # Skip existing proxy-auth header
                if line.lower().startswith(b'proxy-authorization:'):
                    continue
                # Force Connection: close for non-connect requests to avoid connection exhaustion
                if not is_connect and line.lower().startswith(b'connection:'):
                    headers.extend(b'Connection: close\r\n')
                    connection_header_found = True
                else:
                    headers.extend(line)
            
            if not is_connect and not connection_header_found:
                headers.extend(b'Connection: close\r\n')
            
            # Connect to upstream proxy
            try:
                upstream_reader, upstream_writer = await asyncio.wait_for(
                    asyncio.open_connection(self.upstream_host, self.upstream_port),
                    timeout=30
                )
            except Exception as e:
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
                await writer.drain()
                return
            
            # Send request to upstream with auth
            upstream_writer.write(request_line)
            upstream_writer.write(self._get_proxy_auth_header())
            upstream_writer.write(bytes(headers))
            upstream_writer.write(b'\r\n')
            await upstream_writer.drain()
            
            if is_connect:
                # Read upstream response for CONNECT
                try:
                    response_line = await asyncio.wait_for(upstream_reader.readline(), timeout=30)
                except asyncio.TimeoutError:
                    writer.write(b"HTTP/1.1 504 Gateway Timeout\r\nConnection: close\r\n\r\n")
                    await writer.drain()
                    return
                
                # Read remaining response headers
                while True:
                    try:
                        line = await asyncio.wait_for(upstream_reader.readline(), timeout=10)
                    except asyncio.TimeoutError:
                        break
                    if line == b'\r\n' or not line:
                        break
                
                # Check for success
                if b'200' in response_line:
                    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    await writer.drain()
                    
                    # Bidirectional tunnel
                    async def forward(src, dst, name):
                        try:
                            while self.running:
                                try:
                                    data = await asyncio.wait_for(src.read(65536), timeout=300)
                                    if not data:
                                        break
                                    dst.write(data)
                                    await dst.drain()
                                except asyncio.TimeoutError:
                                    break
                                except (ConnectionResetError, BrokenPipeError):
                                    break
                        except Exception:
                            pass
                    
                    # Run both directions
                    task1 = asyncio.create_task(forward(reader, upstream_writer, "client->upstream"))
                    task2 = asyncio.create_task(forward(upstream_reader, writer, "upstream->client"))
                    self._tasks.add(task1)
                    self._tasks.add(task2)
                    
                    try:
                        done, pending = await asyncio.wait(
                            [task1, task2],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in pending:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                    finally:
                        self._tasks.discard(task1)
                        self._tasks.discard(task2)
                else:
                    writer.write(response_line)
                    await writer.drain()
            else:
                # Regular HTTP request - forward response
                try:
                    while True:
                        data = await asyncio.wait_for(upstream_reader.read(65536), timeout=60)
                        if not data:
                            break
                        writer.write(data)
                        await writer.drain()
                except asyncio.TimeoutError:
                    pass
                except (ConnectionResetError, BrokenPipeError):
                    pass
                    
        except Exception as e:
            pass
        finally:
            # Cleanup
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            if upstream_writer:
                try:
                    upstream_writer.close()
                    await upstream_writer.wait_closed()
                except:
                    pass
    
    async def _start_server(self):
        """Start the async server."""
        self.server = await asyncio.start_server(
            self._handle_client,
            '127.0.0.1',
            self.local_port,
            reuse_address=True
        )
        self.running = True
        logger.info(f"Proxy forwarder listening on 127.0.0.1:{self.local_port}")
        
        try:
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            pass
    
    def _run_loop(self):
        """Run the event loop in a thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # Suppress task destroyed warnings
        def exception_handler(loop, context):
            if 'exception' in context:
                exc = context['exception']
                if isinstance(exc, (asyncio.CancelledError, GeneratorExit)):
                    return
            # Log other exceptions
            pass
        
        self._loop.set_exception_handler(exception_handler)
        
        try:
            self._loop.run_until_complete(self._start_server())
        except:
            pass
        finally:
            # Cancel all pending tasks
            for task in self._tasks:
                task.cancel()
            self._loop.close()
    
    def start(self) -> bool:
        """Start the proxy forwarder in a background thread."""
        try:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            
            # Wait a bit for server to start
            import time
            for _ in range(20):
                time.sleep(0.05)
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = s.connect_ex(('127.0.0.1', self.local_port))
                    s.close()
                    if result == 0:
                        return True
                except:
                    pass
            return False
        except Exception as e:
            logger.error(f"Failed to start proxy forwarder: {e}")
            return False
    
    def stop(self):
        """Stop the proxy forwarder."""
        self.running = False
        if self._loop and self._loop.is_running():
            # Cancel all tasks
            for task in list(self._tasks):
                self._loop.call_soon_threadsafe(task.cancel)
            # Stop the server
            if self.server:
                self._loop.call_soon_threadsafe(self.server.close)
            self._loop.call_soon_threadsafe(self._loop.stop)


@dataclass
class ProxyForwarder:
    """Represents a local proxy forwarder instance."""
    profile_name: str
    local_port: int
    upstream_host: str
    upstream_port: int
    username: str
    password: str
    server: Optional[ProxyForwarderServer] = None


class ProxyManager:
    """Manages local proxy forwarders for each profile."""
    
    # Store active forwarders: profile_name -> ProxyForwarder
    _forwarders: Dict[str, ProxyForwarder] = {}
    
    # Port range for local proxies
    _port_start = 18000
    _port_end = 19000
    _next_port = 18000
    
    @classmethod
    def _find_free_port(cls) -> int:
        """Find a free port for the local proxy."""
        for port in range(cls._next_port, cls._port_end):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1', port))
                    cls._next_port = port + 1
                    return port
            except OSError:
                continue
        
        # Reset and try from start
        cls._next_port = cls._port_start
        for port in range(cls._port_start, cls._port_end):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1', port))
                    cls._next_port = port + 1
                    return port
            except OSError:
                continue
        
        raise RuntimeError("No free ports available for proxy forwarder")
    
    @classmethod
    def start_forwarder(cls, profile_name: str, proxy: dict) -> Optional[int]:
        """
        Start a local proxy forwarder for a profile.
        """
        proxy_ip = proxy.get("ip")
        proxy_port = proxy.get("port")
        proxy_user = proxy.get("username")
        proxy_pass = proxy.get("password")
        
        if not all([proxy_ip, proxy_port, proxy_user, proxy_pass]):
            logger.warning(f"Incomplete proxy configuration for {profile_name}")
            return None
        
        # Stop existing forwarder if any
        cls.stop_forwarder(profile_name)
        
        try:
            local_port = cls._find_free_port()
            
            # Create and start server
            server = ProxyForwarderServer(
                local_port=local_port,
                upstream_host=proxy_ip,
                upstream_port=int(proxy_port),
                username=proxy_user,
                password=proxy_pass
            )
            
            if server.start():
                forwarder = ProxyForwarder(
                    profile_name=profile_name,
                    local_port=local_port,
                    upstream_host=proxy_ip,
                    upstream_port=int(proxy_port),
                    username=proxy_user,
                    password=proxy_pass,
                    server=server
                )
                cls._forwarders[profile_name] = forwarder
                
                logger.info(f"Started proxy forwarder for {profile_name}: localhost:{local_port} -> {proxy_ip}:{proxy_port}")
                return local_port
            else:
                logger.error(f"Failed to start proxy forwarder for {profile_name}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to start proxy forwarder for {profile_name}: {e}")
            return None
    
    @classmethod
    def stop_forwarder(cls, profile_name: str) -> bool:
        """Stop a proxy forwarder for a profile."""
        if profile_name in cls._forwarders:
            forwarder = cls._forwarders[profile_name]
            if forwarder.server:
                forwarder.server.stop()
            del cls._forwarders[profile_name]
            logger.info(f"Stopped proxy forwarder for {profile_name}")
            return True
        return False
    
    @classmethod
    def stop_all(cls) -> None:
        """Stop all proxy forwarders."""
        for profile_name in list(cls._forwarders.keys()):
            cls.stop_forwarder(profile_name)
        logger.info("Stopped all proxy forwarders")
    
    @classmethod
    def get_local_port(cls, profile_name: str) -> Optional[int]:
        """Get the local port for a profile's proxy forwarder."""
        if profile_name in cls._forwarders:
            return cls._forwarders[profile_name].local_port
        return None

    @classmethod
    async def handle_cdp_auth(cls, debug_port: int, username: str, password: str, stop_event: asyncio.Event):
        """Keep a CDP connection open to handle proxy authentication challenges natively."""
        import websockets
        import json
        import httpx
        
        # Open debug log file
        log_path = "/Users/azhar/Herd/youtube/python/cdp_debug.log"
        def write_log(msg):
            try:
                with open(log_path, "a") as f:
                    f.write(f"{msg}\n")
            except:
                pass
        
        write_log(f"CDP Auth started for port {debug_port}")
        
        ws_url = None
        # Try to fetch version/target details to get the browser WebSocket URL
        for attempt in range(15):
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"http://127.0.0.1:{debug_port}/json/version")
                    if response.status_code == 200:
                        version_data = response.json()
                        ws_url = version_data.get("webSocketDebuggerUrl")
                        if ws_url:
                            if "localhost" in ws_url:
                                ws_url = ws_url.replace("localhost", "127.0.0.1")
                            write_log(f"CDP Auth: Found ws_url {ws_url} on attempt {attempt}")
                            break
            except Exception as e:
                write_log(f"CDP Auth Attempt {attempt} failed: {e}")
            await asyncio.sleep(0.5)
            
        if not ws_url:
            write_log(f"CDP Auth: Failed to get browser WebSocket URL on port {debug_port}")
            return
            
        write_log(f"CDP Auth: Connecting to {ws_url}")
        try:
            async with websockets.connect(ws_url, max_size=None) as ws:
                msg_id = 1
                pending_runs = {}
                
                # Enable Auto-Attach with waitForDebuggerOnStart to capture new targets and pause them
                # This guarantees we don't miss any request on startup.
                attach_cmd = {
                    "id": msg_id,
                    "method": "Target.setAutoAttach",
                    "params": {
                        "autoAttach": True,
                        "waitForDebuggerOnStart": True,
                        "flatten": True
                    }
                }
                msg_id += 1
                await ws.send(json.dumps(attach_cmd))
                write_log("CDP Auth: Sent Target.setAutoAttach")
                
                # Listen for events
                while not stop_event.is_set():
                    try:
                        # Periodic check on timeout to support clean cancellation
                        message_str = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        write_log(f"CDP Message: {message_str}")
                        message = json.loads(message_str)
                        method = message.get("method")
                        msg_response_id = message.get("id")
                        
                        # If Fetch.enable has been configured for a session, resume execution
                        if msg_response_id and msg_response_id in pending_runs:
                            session_id = pending_runs.pop(msg_response_id)
                            resume_cmd = {
                                "id": msg_id,
                                "method": "Runtime.runIfWaitingForDebugger",
                                "sessionId": session_id
                            }
                            msg_id += 1
                            await ws.send(json.dumps(resume_cmd))
                            write_log(f"CDP Auth: Resumed session {session_id} after Fetch.enable confirmation")
                        
                        if method == "Target.attachedToTarget":
                            params = message.get("params", {})
                            session_id = params.get("sessionId")
                            target_info = params.get("targetInfo", {})
                            write_log(f"CDP Auth: Target attached! Type: {target_info.get('type')}, Session: {session_id}")
                            
                            # Enable Fetch on this session only for Document (main page HTML) requests
                            session_enable = {
                                "id": msg_id,
                                "method": "Fetch.enable",
                                "sessionId": session_id,
                                "params": {
                                    "handleAuthRequests": True,
                                    "patterns": [{"urlPattern": "*", "resourceType": "Document", "requestStage": "Request"}]
                                }
                            }
                            pending_runs[msg_id] = session_id
                            msg_id += 1
                            await ws.send(json.dumps(session_enable))
                            write_log(f"CDP Auth: Sent Fetch.enable for session {session_id}")
                            
                        elif method == "Fetch.authRequired":
                            params = message.get("params", {})
                            request_id = params.get("requestId")
                            auth_challenge = params.get("authChallenge", {})
                            session_id = message.get("sessionId")
                            
                            write_log(f"CDP Auth: Responding to challenge from {auth_challenge.get('origin')} ({auth_challenge.get('source')}) (Session: {session_id})")
                            
                            auth_resp = {
                                "id": msg_id,
                                "method": "Fetch.continueWithAuth",
                                "sessionId": session_id,
                                "params": {
                                    "requestId": request_id,
                                    "authChallengeResponse": {
                                        "response": "ProvideCredentials",
                                        "username": username,
                                        "password": password
                                    }
                                }
                            }
                            if session_id:
                                auth_resp["sessionId"] = session_id
                            msg_id += 1
                            await ws.send(json.dumps(auth_resp))
                            write_log("CDP Auth: Credentials sent successfully")
                            
                        elif method == "Fetch.requestPaused":
                            # Safe fallback: let Document requests continue immediately
                            session_id = message.get("sessionId")
                            params = message.get("params", {})
                            request_id = params.get("requestId")
                            cont_resp = {
                                "id": msg_id,
                                "method": "Fetch.continueRequest",
                                "params": {
                                    "requestId": request_id
                                }
                            }
                            if session_id:
                                cont_resp["sessionId"] = session_id
                            msg_id += 1
                            await ws.send(json.dumps(cont_resp))
                            
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        write_log(f"CDP Auth: Browser closed WebSocket connection on port {debug_port}")
                        break
        except Exception as e:
            write_log(f"CDP Auth: Exception in handler on port {debug_port}: {e}")


# Singleton instance
proxy_manager = ProxyManager()

