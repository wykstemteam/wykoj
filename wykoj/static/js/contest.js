// Show contest start/end countdown on contest page

import { contestCountdown } from "./contestcountdown.js";

$(async () => {
    if ($("#countdown").length) {
        const contestID = location.pathname.match(/\/contest\/(\d+)/)[1];
        contestCountdown(contestID, $("#countdown"));
    }
});
