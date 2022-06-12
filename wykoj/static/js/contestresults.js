// Refresh leaderboard during contest

import { reloadPage } from "./utils.js";

$(async () => {
    const contestID = location.pathname.match(/\/contest\/(\d+)/)[1];
    const resp = await fetch(`/api/contest/${contestID}`);
    const data = await resp.json();
    if (data.status !== "ended") {
        setTimeout(reloadPage, 15 * 1000);
    }
});
