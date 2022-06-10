// Mobile menu dropdown animation

let menuIconDisabled = false;

$(() => {
    $(".menu-icon").click(() => {
        const menuWrapper = $(".menu-wrapper");
        if (menuIconDisabled) {  // Still sliding
            return;
        }
        menuIconDisabled = true;
        if (menuWrapper.width() === 0) {
            menuWrapper.width("100%");
            // Set search bar width to prevent glitching when sliding
            $(".search").width($("nav").width() - 16);  // 8px padding on left and right
            $(".search-results").width($(".search").width());
            $(".menu").slideToggle("fast", () => menuIconDisabled = false);
        } else {
            $(".menu").slideToggle("fast", () => {
                menuWrapper.width(0);
                menuIconDisabled = false;
            });
        }
    });
});
