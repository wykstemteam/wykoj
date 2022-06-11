// Show contest start/end countdown on contest page

import { reloadPage } from "./utils.js";

let targetDate = null;

function pad(n) {
    return String(n).padStart(2, "0");
}

function showCountdown() {
    const diff = targetDate - Date.now();
    if (diff <= 0) {
        reloadPage();
    }

    let seconds = Math.floor(diff / 1000);
    let days = Math.floor(seconds / (24 * 60 * 60));
    seconds -= days * 24 * 60 * 60;
    let hours = Math.floor(seconds / (60 * 60));
    seconds -= hours * 60 * 60;
    let minutes = Math.floor(seconds / 60);
    seconds -= minutes * 60;

    let text = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    if (days) {
        text = `${days} day${days === 1 ? "" : "s"} ${text}`;
    }
    $("#countdown").text(text);
    setTimeout(showCountdown, 100);
}

$(() => {
    if ($("#contest-start-datetime").length) {
        targetDate = Date.parse($("#contest-start-datetime").text());
        setTimeout(showCountdown, 100);
    } else if ($("#contest-end-datetime").length) {
        targetDate = Date.parse($("#contest-end-datetime").text());
        setTimeout(showCountdown, 100);
    }
});
