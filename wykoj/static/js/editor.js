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

export { aceLang, createEditor };
