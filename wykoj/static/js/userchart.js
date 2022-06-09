import { getColor } from "./color.js";

$(() => {
    const ctx = $("canvas")[0].getContext("2d");
    const username = window.location.pathname.match(/\/user\/([a-zA-Z0-9]+)$/)[1];
    $.getJSON(`/user/${username}/submission_languages`, (data) => {
        // Doughnut chart for submission language distribution
        const chart = new Chart(ctx, {
            type: "doughnut",
            data: {
                datasets: [{
                    data: data["occurrences"],
                    backgroundColor: Array.from(
                        { length: data["occurrences"].length }, getColor
                    )
                }],
                labels: data["languages"]
            }
        });
    });
});
