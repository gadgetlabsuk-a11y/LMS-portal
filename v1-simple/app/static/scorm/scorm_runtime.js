// SCORM 1.2 Runtime API wrapper
(function (window) {
  "use strict";

  var API = null;
  var initialized = false;
  var finished = false;
  var sessionStart = Date.now();
  var data = {};

  function findAPI(win) {
    var attempts = 0;
    while (!win.API && win.parent && win.parent !== win && attempts < 10) {
      win = win.parent;
      attempts++;
    }
    return win.API || null;
  }

  function getAPI() {
    if (API) return API;
    API = findAPI(window);
    if (!API && window.opener) API = findAPI(window.opener);
    return API;
  }

  function scormCall(fn, args) {
    var api = getAPI();
    if (!api) return "";
    try {
      return api[fn].apply(api, args);
    } catch (e) {
      console.warn("SCORM API error:", fn, e);
      return "";
    }
  }

  var SCORM = {
    initialize: function () {
      if (initialized || finished) return false;
      var result = scormCall("LMSInitialize", [""]);
      initialized = result === "true" || result === true;
      return initialized;
    },

    setValue: function (element, value) {
      if (!initialized) return false;
      data[element] = value;
      return scormCall("LMSSetValue", [element, String(value)]) === "true";
    },

    getValue: function (element) {
      if (!initialized) return "";
      return scormCall("LMSGetValue", [element]);
    },

    commit: function () {
      if (!initialized) return false;
      return scormCall("LMSCommit", [""]) === "true";
    },

    finish: function () {
      if (!initialized || finished) return false;
      finished = true;
      initialized = false;
      return scormCall("LMSFinish", [""]) === "true";
    },

    setStatus: function (status) {
      // status: incomplete | completed | passed | failed
      this.setValue("cmi.core.lesson_status", status);
      this.commit();
    },

    setScore: function (raw, min, max) {
      this.setValue("cmi.core.score.raw", raw);
      if (min !== undefined) this.setValue("cmi.core.score.min", min);
      if (max !== undefined) this.setValue("cmi.core.score.max", max);
      this.commit();
    },

    setLocation: function (slideId) {
      this.setValue("cmi.core.lesson_location", String(slideId));
      this.commit();
    },

    getLocation: function () {
      return this.getValue("cmi.core.lesson_location");
    },

    setSessionTime: function () {
      var elapsed = Math.floor((Date.now() - sessionStart) / 1000);
      var h = Math.floor(elapsed / 3600);
      var m = Math.floor((elapsed % 3600) / 60);
      var s = elapsed % 60;
      var pad = function (n) { return String(n).padStart(2, "0"); };
      this.setValue("cmi.core.session_time", pad(h) + ":" + pad(m) + ":" + pad(s));
    },
  };

  // Auto-initialize on load
  window.addEventListener("load", function () {
    SCORM.initialize();
  });

  // Auto-finish on unload
  window.addEventListener("beforeunload", function () {
    SCORM.setSessionTime();
    SCORM.finish();
  });

  window.SCORM = SCORM;
})(window);
