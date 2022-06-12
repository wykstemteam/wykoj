import { contestCountdown } from "./contestcountdown.js";
import { sleep } from "./utils.js";

// Home title animation

const hiddenChar = "\u200c";
const homeText = "Welcome to WYK Online Judge!";
const code = [
    `printf("${homeText}\\n");`,       // C
    `cout << "${homeText}" << endl;`,  // C++
    `print("${homeText}")`,            // Python
    `print_endline "${homeText}";;`    // OCaml
];

let typingIndex = 0;

async function typingFx() {
    const typingArea = $(".typing-fx");
    for (let i = 0; i < 2; i++) {
        await sleep(500);
        typingArea.toggleClass("cursor");
    }
    for (let i = 1; i <= code[typingIndex].length; i++) {
        await sleep(75);
        typingArea.text(code[typingIndex].substr(0, i));
    }
    for (let i = 0; i < 6; i++) {
        await sleep(500);
        typingArea.toggleClass("cursor");
    }
    for (let i = code[typingIndex].length; i >= 1; i--) {
        await sleep(25);
        typingArea.text(code[typingIndex].substr(0, i));
    }
    await sleep(25);
    typingArea.text(hiddenChar);  // Maintain height of typingArea with hiddenChar
    typingIndex = (typingIndex + 1) % code.length;
    setTimeout(typingFx, 0);
}

$(() => {
    $(".typing-fx").toggleClass("cursor");
    setTimeout(typingFx, 0);

    // Contest countdowns
    $(".contest-countdown").each(function () {
        contestCountdown($(this).data("contest-id"), $(this));
    });
});
