function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// Mobile menu dropdown animation
let menuIconDisabled = false;

$(".menu-icon").click(() => {
    menuWrapper = $(".menu-wrapper");
    if (menuIconDisabled)  // Still sliding
        return;
    menuIconDisabled = true;
    if (menuWrapper.width() === 0) {
        menuWrapper.width("100%");
        // Set search bar width to prevent glitching when sliding
        $(".search").width($("nav").width() - 16);  // 8px padding on left and right
        $(".search-results").width($(".search").width());
        $(".menu").slideToggle("fast", () => menuIconDisabled = false);
    } else
        $(".menu").slideToggle("fast", () => {
            menuWrapper.width(0);
            menuIconDisabled = false;
        });
});


// Home title animation
const hiddenChar = "\u200c";
const homeText = "Welcome to WYK Online Judge!";
const code = [
    `printf("${homeText}\\n");`,                    // C
    `print("${homeText}")`,                         // Python
    `writeln("${homeText}");`,                      // Pascal
    `print_endline "${homeText}";;`                 // OCaml
]

// Long text should only display on wider screens
if ($(window).width() >= 1100)
    code.push(
        `std::cout << "${homeText}" << std::endl;`, // C++
        // `Console.WriteLine("${homeText}");`,        // C#
        // `System.out.println("${homeText}");`        // Java
    );

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


let colorIndex = 0;
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

function getColor() {
    const color = colors[colorIndex];
    colorIndex = (colorIndex + 1) % colors.length;
    return color;
}


// Show contest start/end countdown on contest page
let targetDate = undefined;

async function showCountdown() {
    diff = targetDate - Date.now();
    if (diff <= 0) {
        $("#countdown").text("00:00:00");
        location = location;  // Reload page
        return;
    }
    let seconds = Math.floor(diff / 1000);
    let days = Math.floor(seconds / (24 * 60 * 60));
    seconds -= days * 24 * 60 * 60;
    let hours = Math.floor(seconds / (60 * 60));
    seconds -= hours * 60 * 60;
    let minutes = Math.floor(seconds / 60);
    seconds -= minutes * 60;
    if (days) {
        $("#countdown").text(
            `${days} day${days == 1 ? "" : "s"} `
            + `${('0' + hours).slice(-2)}:${('0' + minutes).slice(-2)}:${('0' + seconds).slice(-2)}`
        );
    } else {
        $("#countdown").text(
            `${('0' + hours).slice(-2)}:${('0' + minutes).slice(-2)}:${('0' + seconds).slice(-2)}`
        );
    }
    setTimeout(showCountdown, 100);
}


// Ace code editor language conversion
const aceLang = {
    "C": "c_cpp",
    "C++": "c_cpp",
    "Python": "python",
    "OCaml": "ocaml"
}


function renderMath(elem) {
    renderMathInElement(elem, {
        delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false }
        ]
    });
}


// Document ready
$(async () => {
    $(".render_math").each((i, e) => renderMath(e));
    $("[data-bs-toggle='tooltip']").tooltip();  // Enable tooltips globally

    if (window.location.pathname === "/") {
        $(".typing-fx").toggleClass("cursor");
        setTimeout(typingFx, 0);
    } else if (window.location.pathname === "/admin/sidebar") {
        // Editor
        const editor = ace.edit("editor", {
            mode: "ace/mode/html",
            theme: "ace/theme/textmate",
            fontSize: 15,
            showPrintMargin: false
        });

        $("#content").val(editor.getValue());
        $(".sidebar-preview").html(editor.getValue());

        editor.session.on("change", delta => {
            $("#content").val(editor.getValue());
            $(".sidebar-preview").html(editor.getValue());
        });
    } else if (window.location.pathname.match(/\/admin\/task\/[\w\d]+$/) && $("#editor").length) {
        // Editor
        const editor = ace.edit("editor", {
            mode: "ace/mode/html",
            theme: "ace/theme/textmate",
            fontSize: 15,
            minLines: 15,
            maxLines: 20,
            showPrintMargin: false
        });

        $("#content").val(editor.getValue());
        $(".content-preview").html(editor.getValue());
        renderMath($(".content-preview")[0]);

        editor.session.on("change", delta => {
            $("#content").val(editor.getValue());
            $(".content-preview").html(editor.getValue());
            renderMath($(".content-preview")[0]);
        });
    } else if (window.location.pathname.match(/\/admin\/contest\/\d+$/) && $("#editor").length) {
        // Editor
        const editor = ace.edit("editor", {
            mode: "ace/mode/html",
            theme: "ace/theme/textmate",
            fontSize: 15,
            minLines: 15,
            maxLines: 20,
            showPrintMargin: false
        });

        $("#editorial_content").val(editor.getValue());
        $(".content-preview").html(editor.getValue());
        renderMath($(".content-preview")[0]);

        editor.session.on("change", delta => {
            $("#editorial_content").val(editor.getValue());
            $(".content-preview").html(editor.getValue());
            renderMath($(".content-preview")[0]);
        });
    } else if (window.location.pathname.match(/\/task\/[\w\d]+$/) && $(".sample-io").length) {
        $(".sample-io").click(io => {
            // Copy text to clipboard
            const temp = $("<textarea>");
            $("body").append(temp);
            temp.val(io.target.innerText).select();
            document.execCommand("copy");
            temp.remove();
        })
    } else if (window.location.pathname.match(/\/task\/[\w\d]+\/submit$/) && $("#editor").length) {
        // Editor
        const editor = ace.edit("editor", {
            mode: `ace/mode/${aceLang[$("#language > option:selected").text()]}`,
            theme: "ace/theme/textmate",
            fontSize: 15,
            minLines: 15,
            maxLines: 25,
            showPrintMargin: false
        });

        editor.session.on("change", delta => $("#source_code").val(editor.getValue()));

        $("#language").change(() => {
            editor.setOption(
                "mode", `ace/mode/${aceLang[$("#language > option:selected").text()]}`
            );
        })
    } else if (window.location.pathname == "/admin/guide") {
        // Editors
        const graderEditor = ace.edit("editor-grader", {
            mode: "ace/mode/python",
            theme: "ace/theme/textmate",
            fontSize: 15,
            maxLines: Infinity,
            showPrintMargin: false,
            readOnly: true
        })
        graderEditor.setValue(
            `il = int(input())  # Number of lines in the test case input
test_input = "".join(input() + "\\n" for _ in range(il))  # Test case input
ol = int(input())  # Number of lines in the submission program output
test_output = "".join(input() + "\\n" for _ in range(ol))  # User program output

if ...:
    print("AC")  # Accepted
elif ...:
    print("PS 94.87")  # Partial Score of 94.87 points
else:
    print("WA")  # Wrong Answer`, 1)  // Move cursor to end

        const configEditor = ace.edit("editor-config", {
            mode: "ace/mode/json",
            theme: "ace/theme/textmate",
            fontSize: 15,
            maxLines: Infinity,
            showPrintMargin: false,
            readOnly: true
        })

        configEditor.setValue(
            `{
    "grader": true,
    "grader_file": "grader.cpp",
    "grader_language": "C++",
    "batched": true,
    "points": [20, 30, 50]
}`, 1);
    } else if (window.location.pathname.match(/\/submission\/\d+$/) && $("#editor").length) {
        const editor = ace.edit("editor", {
            mode: `ace/mode/${aceLang[$("#lang").text()]}`,
            theme: "ace/theme/textmate",
            fontSize: 15,
            minLines: 15,
            maxLines: Infinity,
            showPrintMargin: false
        })
    } else if (window.location.pathname.match(/\/contest\/\d+$/)) {
        if ($("#contest-start-datetime").length) {
            targetDate = Date.parse($("#contest-start-datetime").text());
            await showCountdown();
        } else if ($("#contest-end-datetime").length) {
            targetDate = Date.parse($("#contest-end-datetime").text());
            await showCountdown();
        }
    } else if (window.location.pathname.match(/\/user\/[a-zA-Z0-9]+$/) && $("canvas").length) {
        const ctx = $("canvas")[0].getContext("2d");
        const username = Array.from(
            ...window.location.pathname.matchAll(/\/user\/([a-zA-Z0-9]+)$/g)
        )[1];
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
    }

    // Leave confirmation box for task submit page and admin task page
    if (window.location.pathname.match(/(\/task\/[\w\d]+\/submit$)|(\/admin\/task\/[\w\d]+$)/)) {
        // var because global variable
        var confirm = false;
        $(":input").change(() => confirm = true);
        // TODO: Figure out what to do to disable confirmation box on submission
        // $("#form").submit(() => confirm = false);

        window.onbeforeunload = () => confirm ? true : null;
    }

    // Search bar
    if ($(".navbar-search").length) {
        $(".search-results").width($(".search").width());
        $(".search-query").on("keydown", e => {
            if (e.keyCode == 13)
                e.preventDefault();
        });
        $(".search-query").on("input", e => {
            query = $(e.target).val();
            searchResultList = $(".search-result-list");
            searchResultList.empty();
            if (query.length < 3 || query.length > 50) {
                return;
            }
            $.getJSON("/search?query=" + encodeURIComponent(query), (data) => {
                if ($(e.target).val() != query)  // Check if query changed
                    return;
                elements = []
                data["tasks"].forEach(task => {
                    elements.push(`<a href="/task/${task.task_id}" class="search-result-link">
                        <li class="search-result">${task.task_id} - ${task.title}</li>
                    </a>`);
                });
                data["users"].forEach(user => {
                    elements.push(`<a href="/user/${user.username}" class="search-result-link">
                        <li class="search-result">${user.username} - ${user.name}</li>
                    </a>`);
                });
                if ($(e.target).val() != query)  // Check if query changed again
                    return;
                searchResultList.html(
                    elements.join("") || '<li class="search-result no-hover-fx">No results</li>'
                );
            });
        })
    }

    // Refresh pending submission page
    if (
        window.location.pathname.match(/\/submission\/\d+$/)
        && $("#time").length && $("#result").length && $("#result").text() == "Pending"
    ) {
        // Submission time is displayed in HKT
        let submissionDate = Date.parse($("#time").text().replace(" ", "T") + "+08:00");
        if (Date.now() - submissionDate <= 60 * 1000) {  // Within one minute of submission
            await sleep(3000);
            location = location;
        }
    }
    // TODO: Refresh contest results page while contest in progress
    // TODO: Also update timer before and during contest
});
