document.addEventListener(
    "DOMContentLoaded",
    function () {

        const elements =
            document.querySelectorAll(
                ".card, .service, .project, .contact-grid > div"
            );

        elements.forEach(
            function (element, index) {

                element.animate(
                    [
                        {
                            opacity: 0,
                            transform:
                                "translateY(20px)"
                        },
                        {
                            opacity: 1,
                            transform:
                                "translateY(0)"
                        }
                    ],
                    {
                        duration: 650,
                        delay: index * 60,
                        fill: "forwards",
                        easing: "ease-out"
                    }
                );

            }
        );

    }
);
