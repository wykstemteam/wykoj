import { reloadPage } from "./utils.js";

function pad(n) {
    return String(n).padStart(2, "0");
}

function getCountdownText(targetDate) {
    if (targetDate <= Date.now()) {
        return "a moment";
    }

    let seconds = Math.ceil((targetDate - Date.now()) / 1000);
    const days = Math.floor(seconds / (24 * 60 * 60));
    seconds -= days * 24 * 60 * 60;
    const hours = Math.floor(seconds / (60 * 60));
    seconds -= hours * 60 * 60;
    const minutes = Math.floor(seconds / 60);
    seconds -= minutes * 60;

    let text = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    if (days) {
        text = `${days} day${days === 1 ? "" : "s"} ${text}`;
    }
    return text;
}

async function contestCountdown(contestID, elem) {
    const url = `/api/contest/${contestID}`
    const resp = await fetch(url);
    const data = await resp.json();

    let status = data.status;
    let targetDate = data.timestamp * 1000;
    let stop = false;

    async function updateStatus() {
        const resp = await fetch(url);
        const data = await resp.json();

        targetDate = data.timestamp * 1000;
        if (data.status !== status || targetDate <= Date.now()) {
            stop = true;
            reloadPage();
            return;
        }
        setTimeout(updateStatus, 5000);
    }

    function showCountdown() {
        if (stop) {
            return;
        }

        const text = getCountdownText(targetDate)
        elem.text(text);

        if (text === "a moment") {
            reloadPage();
            return;
        }
        setTimeout(showCountdown, 100);
    }

    setTimeout(showCountdown, 0);
    setTimeout(updateStatus, 5000);
}

export { contestCountdown };
