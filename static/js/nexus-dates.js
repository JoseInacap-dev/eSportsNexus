(function () {
    "use strict";

    function spanishLocale() {
        if (typeof flatpickr !== "undefined" && flatpickr.l10ns && flatpickr.l10ns.es) {
            return flatpickr.l10ns.es;
        }
        return "default";
    }

    function initPickers() {
        if (typeof flatpickr === "undefined") {
            return;
        }
        var locale = spanishLocale();

        document.querySelectorAll('input[data-datepicker="date"]').forEach(function (element) {
            flatpickr(element, {
                locale: locale,
                altInput: true,
                altFormat: "d/m/Y",
                dateFormat: "Y-m-d",
                allowInput: true
            });
        });

        document.querySelectorAll('input[data-datepicker="datetime"]').forEach(function (element) {
            flatpickr(element, {
                locale: locale,
                altInput: true,
                altFormat: "d/m/Y H:i",
                dateFormat: "Y-m-d H:i",
                enableTime: true,
                time_24hr: true,
                allowInput: true
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initPickers);
    } else {
        initPickers();
    }
})();
