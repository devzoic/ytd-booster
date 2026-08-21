// Proxy authentication handler
// Credentials will be injected by the profile launcher

const config = {
  username: "PROXY_USERNAME",
  password: "PROXY_PASSWORD"
};

// Listen for auth challenges
chrome.webRequest.onAuthRequired.addListener(
  (details, callback) => {
    console.log("Proxy auth required, auto-filling credentials");
    callback({
      authCredentials: {
        username: config.username,
        password: config.password
      }
    });
  },
  { urls: ["<all_urls>"] },
  ["asyncBlocking"]
);

console.log("Proxy Auth Extension loaded");
