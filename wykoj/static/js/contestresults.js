// Refresh leaderboard during contest

import { reloadPage } from "./utils.js";

$(async () => {
    const contestID = location.pathname.match(/\/contest\/(\d+)/)[1];
    const resp = await fetch(`/api/contest/${contestID}`);
    const data = await resp.json();
    if (data.status !== "ended") {
        setTimeout(reloadPage, 15 * 1000);
    }

    // Toggle showing task ID only vs task ID + name in the results header
    $("#task-id-only").change(function () {
        $(".task-title").toggleClass("d-none", this.checked);
    });
});
