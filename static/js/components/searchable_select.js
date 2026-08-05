/*
 * =========================================================
 * Project : Sridevi Enterprises
 * File    : searchable_select.js
 * Purpose : Shared searchable-dropdown component for the Employee Portal.
 *           A plain .form-control input with a filtered, keyboard-navigable
 *           Bootstrap .list-group suggestion menu underneath - free text is
 *           still allowed on submit unless the caller enforces otherwise.
 *
 *           Extracted from product_form.html (v1.0 Sprint 4, Department/
 *           Category dropdowns) so the Inventory Transaction form's Product
 *           selector (v1.0 Sprint 5.1) can reuse the exact same component
 *           instead of a second implementation - "Do not build another
 *           product search component."
 *
 * Usage   : window.initSearchableSelect(inputId, menuId, getOptions, onSelect)
 *           getOptions() must return an array of { value, label } objects.
 *           onSelect(value, label) is optional - called after a selection
 *           is made (by click or Enter), in addition to the input's own
 *           value being set to `label` and input/change events firing.
 *
 * Author  : Srikar
 * =========================================================
 */

window.initSearchableSelect = function initSearchableSelect(inputId, menuId, getOptions, onSelect) {
    "use strict";

    var input = document.getElementById(inputId);
    var menu = document.getElementById(menuId);
    if (!input || !menu) return null;

    var activeIndex = -1;

    function items() {
        return menu.querySelectorAll(".list-group-item[data-value]");
    }

    function highlight(index) {
        var list = items();
        list.forEach(function (item, i) {
            item.classList.toggle("active", i === index);
        });
        if (list[index]) {
            list[index].scrollIntoView({ block: "nearest" });
        }
    }

    function selectOption(value, label) {
        input.value = label;
        close();
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        if (typeof onSelect === "function") {
            onSelect(value, label);
        }
    }

    function close() {
        menu.hidden = true;
        input.setAttribute("aria-expanded", "false");
        activeIndex = -1;
    }

    function open(filterText) {
        var options = getOptions();
        var query = (filterText || "").trim().toLowerCase();
        var matches = query
            ? options.filter(function (opt) { return opt.label.toLowerCase().indexOf(query) !== -1; })
            : options;

        menu.innerHTML = "";
        activeIndex = -1;

        if (options.length === 0) {
            close();
            return;
        }

        if (matches.length === 0) {
            var empty = document.createElement("li");
            empty.className = "list-group-item list-group-item-empty";
            empty.textContent = "No matches";
            menu.appendChild(empty);
        } else {
            matches.forEach(function (opt) {
                var item = document.createElement("li");
                item.className = "list-group-item list-group-item-action";
                item.setAttribute("role", "option");
                item.setAttribute("data-value", opt.value);
                item.textContent = opt.label;
                // mousedown (not click) fires before the input's blur closes the menu.
                item.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    selectOption(opt.value, opt.label);
                });
                menu.appendChild(item);
            });
        }

        menu.hidden = false;
        input.setAttribute("aria-expanded", "true");
    }

    input.addEventListener("input", function () {
        open(input.value);
    });

    input.addEventListener("focus", function () {
        open(input.value);
    });

    input.addEventListener("keydown", function (e) {
        if (menu.hidden) return;
        var list = items();
        if (list.length === 0) return;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, list.length - 1);
            highlight(activeIndex);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            highlight(activeIndex);
        } else if (e.key === "Enter") {
            if (activeIndex >= 0 && list[activeIndex]) {
                e.preventDefault();
                var el = list[activeIndex];
                selectOption(el.getAttribute("data-value"), el.textContent);
            }
        } else if (e.key === "Escape") {
            close();
        }
    });

    input.addEventListener("blur", function () {
        // Delayed so a mousedown-selected option registers before the menu closes.
        window.setTimeout(close, 100);
    });

    return { refresh: function () { if (!menu.hidden) open(input.value); } };
};
