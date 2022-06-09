const colors = [
    "rgb(114,229,239)",
    "rgb(33,166,69)",
    "rgb(148,234,91)",
    "rgb(104,149,188)",
    "rgb(33,240,182)",
    "rgb(31,161,152)",
    "rgb(187,207,122)",
    "rgb(255,77,130)",
    "rgb(255,178,190)",
    "rgb(198,129,54)"
];
let colorIndex = 0;

function getColor() {
    const color = colors[colorIndex];
    colorIndex = (colorIndex + 1) % colors.length;
    return color;
}

export { getColor };
