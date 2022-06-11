// Show contest start/end countdown on contest page

import { reloadPage } from "./utils.js";

let status = null;
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

async function updateStatus() {
    let resp = await fetch(`${location.pathname}/status`);
    let data = await resp.json();

    if (data.status !== status) {
        reloadPage();
    }
    targetDate = data.timestamp * 1000;
    setTimeout(updateStatus, 3000);
}

$(async () => {
    let resp = await fetch(`${location.pathname}/status`);
    let data = await resp.json();
    if (data.status !== "ended") {
        status = data.status;
        targetDate = data.timestamp * 1000;
        setTimeout(showCountdown, 0);
        setTimeout(updateStatus, 3000);
    }
});
