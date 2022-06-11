import { renderMath } from "./utils.js";

// Ace code editor language conversion
const aceLang = {
    "C": "c_cpp",
    "C++": "c_cpp",
    "Python": "python",
    "OCaml": "ocaml"
}

function createEditor(id, language, params) {
    const obj = $.extend({
        mode: `ace/mode/${language}`,
        theme: "ace/theme/textmate",
        fontSize: 15,
        showPrintMargin: false
    }, params);
    const editor = ace.edit(id, obj);
    return editor;
}

function bindToEditor(editor, content, preview) {
    const update = (triggerChange) => {
        const res = content.val(editor.getValue());
        if (triggerChange) {
            res.trigger("change");
        }
        if (preview === null) {
            return;
        }
        preview.html(editor.getValue());
        if (preview.hasClass("render-math")) {
            renderMath(preview[0]);
        }
    }

    update(false);
    editor.session.on("change", () => update(true));
}

async function initEditorContentFromURL(editor, url) {
    let resp = await fetch(url);
    let code = await resp.text();
    editor.setValue(code, 1);  // Move cursor to end
}

export { aceLang, createEditor, bindToEditor, initEditorContentFromURL };
