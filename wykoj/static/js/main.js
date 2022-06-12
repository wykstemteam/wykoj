import { aceLang, createEditor, bindToEditor, initEditorContentFromURL } from "./editor.js";
import { renderMath, copyTextToClipboard } from "./utils.js";
import "./mobilemenu.js";
import "./search.js";

$(async () => {
    $(".render-math").each((i, e) => renderMath(e));
    $("[data-bs-toggle='tooltip']").tooltip();  // Enable tooltips globally

    // Leave confirmation dialog for pages with input EXCEPT SEARCH BAR (TODO)
    if ($(":input").length) {
        let askConfirm = false;
        $(":input").change(() => {
            askConfirm = true;
        });
        $("form").submit(() => {
            askConfirm = false;
        });
        window.onbeforeunload = () => (askConfirm ? true : null);
    }

    // Copy sample test cases to clipboard
    if ($(".sample-io").length) {
        $(".sample-io").click(e => copyTextToClipboard(e.target));
    }

    // Code editors
    if (location.pathname.match(/\/task\/[\w\d]+\/submit$/) && $("#editor").length) {
        const language = $("#language > option:selected").text();
        const editor = createEditor("editor", aceLang[language], { minLines: 15, maxLines: 25 });
        bindToEditor(editor, $("#source_code"), null);

        $("#language").change(() => {
            const language = $("#language > option:selected").text();
            editor.setOption("mode", `ace/mode/${aceLang[language]}`);
        });
    } else if (location.pathname.match(/\/submission\/\d+$/) && $("#editor").length) {
        const language = $("#lang").text();
        const editor = createEditor("editor", aceLang[language], { minLines: 15, maxLines: Infinity });
    } else if (location.pathname === "/admin/sidebar") {
        const editor = createEditor("editor", "html");
        bindToEditor(editor, $("#content"), $(".sidebar-preview"));
    } else if (location.pathname.match(/\/admin\/task\/[\w\d]+$/) && $("#editor").length) {
        const editor = createEditor("editor", "html", { minLines: 15, maxLines: 20 });
        bindToEditor(editor, $("#content"), $(".content-preview"));
    } else if (location.pathname.match(/\/admin\/contest\/\d+$/) && $("#editor").length) {
        const editor = createEditor("editor", "html", { minLines: 15, maxLines: 20 });
        bindToEditor(editor, $("#editorial_content"), $(".content-preview"));
    } else if (location.pathname === "/admin/guide") {
        const graderEditor = createEditor("editor-grader", "python", { maxLines: Infinity, readOnly: true });
        initEditorContentFromURL(graderEditor, "/static/editor/grader.py");

        const configEditor = createEditor("editor-config", "json", { maxLines: Infinity, readOnly: true });
        initEditorContentFromURL(configEditor, "/static/editor/config.json");
    }
});
