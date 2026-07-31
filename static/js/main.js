/*
=========================================================
Project : Sridevi Enterprises
File    : main.js
Purpose : Shared front-end behavior for the customer site.

Author  : Srikar
=========================================================
*/

document.addEventListener("DOMContentLoaded", function () {
    initFeaturedCategoriesSliders();
    initCategorySearch();
    initProductGallery();
});

function initFeaturedCategoriesSliders() {
    var wrappers = document.querySelectorAll(".featured-categories-slider-wrapper");

    wrappers.forEach(function (wrapper) {
        var slider = wrapper.querySelector(".featured-categories-slider");
        var prevButton = wrapper.querySelector(".slider-arrow-prev");
        var nextButton = wrapper.querySelector(".slider-arrow-next");

        if (!slider || !prevButton || !nextButton) {
            return;
        }

        function scrollStep() {
            var firstSlide = slider.querySelector(".category-slide");
            var sliderGap = parseFloat(window.getComputedStyle(slider).columnGap || 20);

            if (!firstSlide) {
                return slider.clientWidth;
            }

            return firstSlide.getBoundingClientRect().width + sliderGap;
        }

        function updateArrowState() {
            var edgeTolerance = 2;
            var maxScrollLeft = slider.scrollWidth - slider.clientWidth;
            var hasOverflow = maxScrollLeft > edgeTolerance;

            wrapper.classList.toggle("slider-no-overflow", !hasOverflow);

            prevButton.disabled = !hasOverflow || slider.scrollLeft <= edgeTolerance;
            nextButton.disabled = !hasOverflow || slider.scrollLeft >= maxScrollLeft - edgeTolerance;
        }

        prevButton.addEventListener("click", function () {
            slider.scrollBy({ left: -scrollStep(), behavior: "smooth" });
        });

        nextButton.addEventListener("click", function () {
            slider.scrollBy({ left: scrollStep(), behavior: "smooth" });
        });

        slider.addEventListener("scroll", updateArrowState);
        window.addEventListener("resize", updateArrowState);

        updateArrowState();
    });
}

function initCategorySearch() {
    var searchInput = document.getElementById("category-search");
    var grid = document.getElementById("category-grid");

    if (!searchInput || !grid) {
        return;
    }

    var cards = grid.querySelectorAll(".category-grid-card");
    var emptyState = document.getElementById("category-empty-state");

    searchInput.addEventListener("input", function () {
        var query = searchInput.value.trim().toLowerCase();
        var visibleCount = 0;

        cards.forEach(function (card) {
            var matches = card.dataset.categoryName.indexOf(query) !== -1;
            card.classList.toggle("d-none", !matches);

            if (matches) {
                visibleCount += 1;
            }
        });

        if (emptyState) {
            emptyState.classList.toggle("d-none", visibleCount !== 0);
        }
    });
}

function initProductGallery() {
    var gallery = document.querySelector(".product-gallery");
    var heroImage = document.getElementById("product-hero-image");

    if (!gallery || !heroImage) {
        return;
    }

    var thumbs = gallery.querySelectorAll(".product-gallery-thumb");
    var fadeDuration = 150;

    thumbs.forEach(function (thumb) {
        thumb.addEventListener("click", function () {
            if (thumb.classList.contains("is-active")) {
                return;
            }

            thumbs.forEach(function (t) {
                t.classList.remove("is-active");
                t.removeAttribute("aria-current");
            });

            thumb.classList.add("is-active");
            thumb.setAttribute("aria-current", "true");

            heroImage.classList.add("is-fading");

            window.setTimeout(function () {
                heroImage.src = thumb.dataset.imageSrc;
                heroImage.alt = thumb.dataset.imageAlt;
                heroImage.classList.toggle("product-main-image--placeholder", thumb.dataset.isPlaceholder === "true");
                heroImage.classList.remove("is-fading");
            }, fadeDuration);
        });
    });
}
