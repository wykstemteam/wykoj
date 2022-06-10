import { aceLang, createEditor } from "./editor.js";
import { sleep, renderMath, copyTextToClipboard, reloadPage } from "./utils.js";
import "./mobilemenu.js";
import "./search.js";

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



    // Refresh pending submission page
    if (
        window.location.pathname.match(/\/submission\/\d+$/)
        && $("#time").length && $("#result").length && $("#result").text() == "Pending"
    ) {
        // Submission time is displayed in HKT
        let submissionDate = Date.parse($("#time").text().replace(" ", "T") + "+08:00");
        if (Date.now() - submissionDate <= 60 * 1000) {  // Within one minute of submission
            await sleep(3000);
            reloadPage();
        }
    }

    // TODO: Refresh contest results page while contest in progress
    // TODO: Also update timer before and during contest
});
