// Refresh pending submission page

import { reloadPage } from "./utils.js";

$(() => {
    if ($("#result").text() !== "Pending") {
        return;
    }

    // Submission time is displayed in HKT
    let submissionDate = Date.parse($("#time").text().replace(" ", "T") + "+08:00");
    if (Date.now() - submissionDate <= 60 * 1000) {  // Within one minute of submission
        setTimeout(reloadPage, 3000);
    }
});
