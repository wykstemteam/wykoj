function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function renderMath(elem) {
    renderMathInElement(elem, {
        delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false }
        ]
    });
}

function copyTextToClipboard(elem) {
    const temp = $("<textarea>");
    $("body").append(temp);
    temp.val(elem.innerText).select();
    document.execCommand("copy");
    temp.remove();
}

function reloadPage() {
    location.reload();
}

export { sleep, renderMath, copyTextToClipboard, reloadPage };
