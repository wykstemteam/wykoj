import { aceLang, createEditor } from "./editor.js";
import { sleep, renderMath, copyTextToClipboard } from "./utils.js";

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
    } else {
        $(".menu").slideToggle("fast", () => {
            menuWrapper.width(0);
            menuIconDisabled = false;
        });
    }
});


// Show contest start/end countdown on contest page
let targetDate = null;

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


// Document ready
$(async () => {
    $(".render_math").each((i, e) => renderMath(e));
    $("[data-bs-toggle='tooltip']").tooltip();  // Enable tooltips globally

    if (window.location.pathname === "/admin/sidebar") {
        const editor = createEditor("editor", "html");

        $("#content").val(editor.getValue());
        $(".sidebar-preview").html(editor.getValue());

        editor.session.on("change", _ => {
            $("#content").val(editor.getValue());
            $(".sidebar-preview").html(editor.getValue());
        });
    } else if (window.location.pathname.match(/\/admin\/task\/[\w\d]+$/) && $("#editor").length) {
        const editor = createEditor("editor", "html", { minLines: 15, maxLines: 20 });

        $("#content").val(editor.getValue());
        $(".content-preview").html(editor.getValue());
        renderMath($(".content-preview")[0]);

        editor.session.on("change", _ => {
            $("#content").val(editor.getValue());
            $(".content-preview").html(editor.getValue());
            renderMath($(".content-preview")[0]);
        });
    } else if (window.location.pathname.match(/\/admin\/contest\/\d+$/) && $("#editor").length) {
        const editor = createEditor("editor", "html", { minLines: 15, maxLines: 20 });

        $("#editorial_content").val(editor.getValue());
        $(".content-preview").html(editor.getValue());
        renderMath($(".content-preview")[0]);

        editor.session.on("change", _ => {
            $("#editorial_content").val(editor.getValue());
            $(".content-preview").html(editor.getValue());
            renderMath($(".content-preview")[0]);
        });
    } else if (window.location.pathname.match(/\/task\/[\w\d]+$/) && $(".sample-io").length) {
        $(".sample-io").click(e =>
            copyTextToClipboard(e.target)
        );
    } else if (window.location.pathname.match(/\/task\/[\w\d]+\/submit$/) && $("#editor").length) {
        const language = aceLang[$("#language > option:selected").text()];
        const editor = createEditor("editor", language, { minLines: 15, maxLines: 25 });

        editor.session.on("change", _ => $("#source_code").val(editor.getValue()));

        $("#language").change(() =>
            editor.setOption(
                "mode", `ace/mode/${aceLang[$("#language > option:selected").text()]}`
            )
        );
    } else if (window.location.pathname == "/admin/guide") {
        const graderEditor = createEditor("editor-grader", "python", { maxLines: Infinity, readOnly: true });

        let resp = await fetch("/static/editor/grader.py");
        let code = await resp.text();
        graderEditor.setValue(code, 1)  // Move cursor to end

        const configEditor = createEditor("editor-config", "json", { maxLines: Infinity, readOnly: true });

        resp = await fetch("/static/editor/config.json");
        code = await resp.text();
        configEditor.setValue(code, 1);
    } else if (window.location.pathname.match(/\/submission\/\d+$/) && $("#editor").length) {
        const language = aceLang[$("#lang").text()];
        const editor = createEditor("editor", language, { minLines: 15, maxLines: Infinity });
    } else if (window.location.pathname.match(/\/contest\/\d+$/)) {
        if ($("#contest-start-datetime").length) {
            targetDate = Date.parse($("#contest-start-datetime").text());
            await showCountdown();
        } else if ($("#contest-end-datetime").length) {
            targetDate = Date.parse($("#contest-end-datetime").text());
            await showCountdown();
        }
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
            // TOOD: Add behavior on enter
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
            location = location;  // Refresh
        }
    }

    // TODO: Refresh contest results page while contest in progress
    // TODO: Also update timer before and during contest
});
