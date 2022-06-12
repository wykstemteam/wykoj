import { getColor } from "./color.js";

$(async () => {
    if ($("canvas").length === 0) {
        // No submissions
        return;
    }

    const ctx = $("canvas")[0].getContext("2d");
    const username = location.pathname.match(/\/user\/([a-zA-Z0-9]+)/)[1];

    const resp = await fetch(`/api/user/${username}`);
    const data = await resp.json();

    // Doughnut chart for submission language distribution
    const chart = new Chart(ctx, {
        type: "doughnut",
        data: {
            datasets: [{
                data: data.submission_languages.occurrences,
                backgroundColor: Array.from(
                    { length: data.submission_languages.occurrences.length }, getColor
                )
            }],
            labels: data.submission_languages.languages
        }
    });
});
