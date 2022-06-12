// Refresh pending submission page

import { reloadPage } from "./utils.js";

$(() => {
    if ($("#result").text() !== "Pending") {
        return;
    }

    const submissionID = location.pathname.match(/\/submission\/(\d+)/)[1];

    async function updateVerdict() {
        let resp = await fetch(`/api/submission/${submissionID}`);
        let data = await resp.json();
        if (data.verdict !== "pe") {
            reloadPage();
            return;
        }
        // Within 5 minutes of submission
        if (Date.now() - data.timestamp * 1000 <= 5 * 60 * 1000) {
            return;
        }
        setTimeout(updateVerdict, 3000);
    }

    setTimeout(updateVerdict, 3000);
});
