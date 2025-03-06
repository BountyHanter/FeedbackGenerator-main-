document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".headerlink").forEach(link => {
        link.removeAttribute("title"); // Убираем стандартный title

        // Создаём кастомный tooltip
        const tooltip = document.createElement("span");
        tooltip.classList.add("custom-tooltip");
        tooltip.textContent = "Ссылка на этот раздел";
        link.appendChild(tooltip);

        // Корректируем позицию по вертикали
        link.style.position = "relative";
    });
});
