document.addEventListener("DOMContentLoaded", () => {
  const firstInput = document.querySelector("input[autofocus]");
  if (firstInput) firstInput.focus();

  document.querySelectorAll("a[href^='#']").forEach((link) => {
    link.addEventListener("click", () => {
      const target = document.querySelector(link.getAttribute("href"));
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
});
