document.addEventListener("DOMContentLoaded", () => {
  const firstInput = document.querySelector("input[autofocus]");
  if (firstInput) firstInput.focus();

  // Smooth scrolling for anchor links
  document.querySelectorAll("a[href^='#']").forEach((link) => {
    link.addEventListener("click", () => {
      const target = document.querySelector(link.getAttribute("href"));
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Don't trigger shortcuts when typing in form inputs
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") {
      return;
    }

    if (e.key === "n" || e.key === "N") {
      // N for new claim
      e.preventDefault();
      window.location.href = "/claims/new";
    } else if (e.key === "Escape") {
      // Escape to go back or close modals
      // For now, go back to claims page if on detail or form
      const currentPath = window.location.pathname;
      if (currentPath.startsWith("/claims/") && currentPath !== "/claims/new") {
        // Check if we're on edit or detail page
        if (currentPath.includes("/edit") || currentPath.match(/^\/claims\/\d+$/)) {
          e.preventDefault();
          window.location.href = "/claims";
        }
      } else if (currentPath.startsWith("/sources/") && currentPath !== "/sources") {
        if (currentPath.includes("/edit") || currentPath.match(/^\/sources\/\d+$/)) {
          e.preventDefault();
          window.location.href = "/sources";
        }
      }
    }
  });

  // Toast notification system
  window.showToast = (message, type = "info") => {
    // Remove any existing toast container
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => {
        container.removeChild(toast);
        if (container.children.length === 0) {
          container.remove();
        }
      }, 300);
    }, 3000);
  };
});