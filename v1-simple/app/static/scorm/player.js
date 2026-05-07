// SCORM Course Player
(function () {
  "use strict";

  var courseData = null;
  var allSlides = [];
  var currentSlideIdx = 0;
  var visitedSlides = new Set();
  var quizScore = null;

  function init(data) {
    courseData = data;
    // Flatten all slides from modules > lessons > slides
    allSlides = [];
    (data.modules || []).forEach(function (mod) {
      (mod.lessons || []).forEach(function (lesson) {
        (lesson.slides || []).forEach(function (slide) {
          allSlides.push(slide);
        });
      });
    });

    // Resume from SCORM location if available
    var location = window.SCORM ? window.SCORM.getLocation() : "";
    if (location) {
      var idx = allSlides.findIndex(function (s) { return String(s.id) === location; });
      if (idx >= 0) currentSlideIdx = idx;
    }

    renderSlide(currentSlideIdx);
    renderNav();
  }

  function renderBlock(block) {
    var p = block.props || {};
    switch (block.type) {
      case "heading":
        return '<h' + (p.level || 2) + ' class="lms-heading" style="text-align:' + (p.align || "left") + '">' + escHtml(p.text || "") + '</h' + (p.level || 2) + '>';
      case "paragraph":
        return '<div class="lms-paragraph" style="text-align:' + (p.align || "left") + '">' + (p.text || "") + '</div>';
      case "image":
        return '<figure class="lms-image"><img src="' + escHtml(p.url || "") + '" alt="' + escHtml(p.alt || "") + '" style="object-fit:' + (p.fit || "contain") + '"/>' + (p.caption ? '<figcaption>' + escHtml(p.caption) + '</figcaption>' : '') + '</figure>';
      case "video":
        return '<video class="lms-video" controls' + (p.autoplay ? ' autoplay' : '') + '><source src="' + escHtml(p.url || "") + '"/></video>';
      case "audio":
        return '<audio class="lms-audio" controls><source src="' + escHtml(p.url || "") + '"/></audio>' + (p.transcript ? '<details><summary>Transcript</summary><p>' + escHtml(p.transcript) + '</p></details>' : '');
      case "divider":
        return '<hr class="lms-divider" style="border-style:' + (p.style || "solid") + '"/>';
      case "spacer":
        return '<div style="height:' + (p.height_px || 24) + 'px"></div>';
      case "bullets":
        var tag = p.style === "number" ? "ol" : "ul";
        return '<' + tag + ' class="lms-bullets">' + (p.items || []).map(function (i) { return '<li>' + escHtml(i) + '</li>'; }).join("") + '</' + tag + '>';
      case "button":
        return '<button class="lms-button" onclick="handleButton(\'' + escHtml(block.id) + '\',' + JSON.stringify(p) + ')">' + escHtml(p.label || "Next") + '</button>';
      case "mcq_single":
      case "mcq_multi":
      case "tf":
        return renderQuizBlock(block);
      default:
        return '<div class="lms-unknown">[' + block.type + ']</div>';
    }
  }

  function renderQuizBlock(block) {
    var p = block.props || {};
    var html = '<div class="lms-quiz" data-block-id="' + block.id + '" data-type="' + block.type + '">';
    html += '<p class="lms-quiz-question">' + escHtml(p.question || "") + '</p>';
    if (block.type === "tf") {
      html += '<label><input type="radio" name="q_' + block.id + '" value="true"/> True</label>';
      html += '<label><input type="radio" name="q_' + block.id + '" value="false"/> False</label>';
    } else {
      var inputType = block.type === "mcq_single" ? "radio" : "checkbox";
      (p.options || []).forEach(function (opt) {
        html += '<label><input type="' + inputType + '" name="q_' + block.id + '" value="' + escHtml(opt.id) + '"/> ' + escHtml(opt.text) + '</label>';
      });
    }
    html += '<button onclick="submitQuiz(\'' + block.id + '\')">Submit</button>';
    html += '<div class="lms-quiz-feedback" id="fb_' + block.id + '" style="display:none"></div>';
    html += '</div>';
    return html;
  }

  function renderSlide(idx) {
    var slide = allSlides[idx];
    if (!slide) return;
    var container = document.getElementById("lms-slide");
    if (!container) return;
    var html = '';
    (slide.blocks || []).forEach(function (block) { html += renderBlock(block); });
    container.innerHTML = html;
    visitedSlides.add(String(slide.id));
    if (window.SCORM) {
      window.SCORM.setStatus("incomplete");
      window.SCORM.setLocation(slide.id);
    }
    checkCompletion();
    renderNav();
  }

  function renderNav() {
    var prev = document.getElementById("btn-prev");
    var next = document.getElementById("btn-next");
    var counter = document.getElementById("slide-counter");
    if (prev) prev.disabled = currentSlideIdx === 0;
    if (next) next.disabled = currentSlideIdx === allSlides.length - 1;
    if (counter) counter.textContent = (currentSlideIdx + 1) + " / " + allSlides.length;
  }

  function checkCompletion() {
    if (!courseData) return;
    var passThreshold = courseData.pass_threshold || 80;
    var allVisited = allSlides.every(function (s) { return visitedSlides.has(String(s.id)); });
    if (quizScore !== null && quizScore >= passThreshold) {
      if (window.SCORM) { window.SCORM.setScore(quizScore, 0, 100); window.SCORM.setStatus("passed"); }
    } else if (allVisited && quizScore === null) {
      if (window.SCORM) window.SCORM.setStatus("completed");
    }
  }

  window.handleButton = function (blockId, props) {
    switch (props.action) {
      case "next": if (currentSlideIdx < allSlides.length - 1) { currentSlideIdx++; renderSlide(currentSlideIdx); } break;
      case "prev": if (currentSlideIdx > 0) { currentSlideIdx--; renderSlide(currentSlideIdx); } break;
      case "complete": if (window.SCORM) { window.SCORM.setStatus("completed"); window.SCORM.finish(); } break;
      case "external": if (props.url) window.open(props.url, "_blank"); break;
    }
  };

  window.submitQuiz = function (blockId) {
    var container = document.querySelector('[data-block-id="' + blockId + '"]');
    if (!container) return;
    var type = container.dataset.type;
    var feedback = document.getElementById("fb_" + blockId);
    // simplified scoring — in real impl check against block data
    if (feedback) { feedback.style.display = "block"; feedback.textContent = "Answer submitted."; }
    checkCompletion();
  };

  window.lmsNext = function () { if (currentSlideIdx < allSlides.length - 1) { currentSlideIdx++; renderSlide(currentSlideIdx); } };
  window.lmsPrev = function () { if (currentSlideIdx > 0) { currentSlideIdx--; renderSlide(currentSlideIdx); } };

  function escHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Expose init
  window.lmsInit = init;
})();
