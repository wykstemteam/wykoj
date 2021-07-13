// MathJax configuation
window.MathJax = {
    tex: {
      inlineMath: [['$', '$'], ['\\(', '\\)']],
    },
    svg: {
      fontCache: "global"
    },
    options: {
      ignoreHtmlClass: "tex2jax_ignore",
      processHtmlClass: "tex2jax_process"
    }
};


// Load MathJax
var script = document.createElement("script");
script.src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js";
script.async = true;
document.head.appendChild(script);
