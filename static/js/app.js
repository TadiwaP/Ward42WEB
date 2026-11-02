/*
  app.js - the JavaScript for Ward 42 Fix-It.

  Every page loads this one file. Each feature below first checks whether
  its part of the page exists, and does nothing if it does not. That way one
  file can serve all the pages.

  Features:
    1. Report form: checks the fields in the browser (no page reload)
    2. Report form: shrinks big photos before upload (saves mobile data)
    3. Report form: saves a draft of the typing in localStorage
    4. All reports page: live filter (no request to the server)
    5. Dashboard: fetch() the JSON counts and show them
    6. Registers the service worker (the offline part of the PWA)

  The server checks everything again. Browser checks are only for
  convenience, because anyone can switch JavaScript off.
*/

"use strict";

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

var DRAFT_KEY = "ward42-report-draft";
var MAX_PHOTO_BYTES = 2 * 1024 * 1024; // 2 MB, same rule as the server
var MAX_PHOTO_SIDE = 1280;             // longest side of a shrunk photo, in pixels
var PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];


// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function byId(id) {
  return document.getElementById(id);
}

// Show an error message next to a field. The templates already have an
// empty "<id>-error" box under every field, and Bootstrap shows it when the
// field has the class "is-invalid".
function showError(field, message) {
  field.classList.add("is-invalid");
  field.setAttribute("aria-invalid", "true");
  var box = byId(field.id + "-error");
  if (box) {
    box.textContent = message;
  }
}

function clearError(field) {
  field.classList.remove("is-invalid");
  field.removeAttribute("aria-invalid");
  var box = byId(field.id + "-error");
  if (box) {
    box.textContent = "";
  }
}

// 1500000 bytes -> "1.4 MB"
function formatSize(bytes) {
  if (bytes >= 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }
  return Math.max(1, Math.round(bytes / 1024)) + " KB";
}


// ---------------------------------------------------------------------------
// 1. Report form: checks in the browser
// ---------------------------------------------------------------------------

// One rule per field. Each rule gets what the person typed and returns an
// error message, or "" when the value is fine. The messages match the server.
var fieldRules = {
  category: function (value) {
    if (value === "") {
      return "Please choose a category.";
    }
    return "";
  },

  street: function (value) {
    value = value.trim();
    if (value === "") {
      return "Please tell us where the fault is.";
    }
    if (value.length > 150) {
      return "Please use 150 characters or fewer.";
    }
    return "";
  },

  description: function (value) {
    value = value.trim();
    if (value === "") {
      return "Please describe the problem.";
    }
    if (value.length < 10 || value.length > 500) {
      return "The description must be between 10 and 500 characters.";
    }
    return "";
  },

  reporter_name: function (value) {
    value = value.trim();
    if (value === "") {
      return "Please enter your name.";
    }
    if (value.length < 2 || value.length > 100) {
      return "Your name must be 2 to 100 characters.";
    }
    return "";
  },

  // 10 digits, starting with 0 (a South African cell number)
  reporter_cell: function (value) {
    value = value.trim();
    if (value === "") {
      return "Please enter your cell number.";
    }
    if (!/^0\d{9}$/.test(value)) {
      return "Enter a 10-digit cell number starting with 0, for example 0821234567.";
    }
    return "";
  }
};

// Check one field. Returns true when it is fine.
function validateField(field) {
  var rule = fieldRules[field.id];
  var message = rule(field.value);
  if (message === "") {
    clearError(field);
    return true;
  }
  showError(field, message);
  return false;
}

// The photo is optional. If one is chosen it must be JPEG, PNG or WebP and
// no bigger than 2 MB.
function validatePhoto(input) {
  var file = input.files && input.files[0];
  if (!file) {
    clearError(input);
    return true;
  }
  if (PHOTO_TYPES.indexOf(file.type) === -1) {
    showError(input, "Photos must be JPEG, PNG or WebP files.");
    return false;
  }
  if (file.size > MAX_PHOTO_BYTES) {
    showError(input, "That photo is too big. Please choose one smaller than 2 MB.");
    return false;
  }
  clearError(input);
  return true;
}


// ---------------------------------------------------------------------------
// 2. Report form: shrink big photos before upload
// ---------------------------------------------------------------------------

// A phone photo is often 3 to 5 MB. On prepaid data that is expensive, and
// the app does not need that much detail. We redraw the photo smaller on a
// hidden canvas and save it as a JPEG. Returns a new File, or null if the
// photo could not be made any smaller.
async function shrinkPhoto(file) {
  if (!window.createImageBitmap) {
    return null; // an old browser: just send the original
  }

  var bitmap = await createImageBitmap(file);
  var width = bitmap.width;
  var height = bitmap.height;

  // Scale down so the longest side is at most MAX_PHOTO_SIDE.
  var longest = Math.max(width, height);
  if (longest > MAX_PHOTO_SIDE) {
    var scale = MAX_PHOTO_SIDE / longest;
    width = Math.round(width * scale);
    height = Math.round(height * scale);
  }

  var canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  var context = canvas.getContext("2d");
  context.fillStyle = "#ffffff"; // a white background in case the photo is a transparent PNG
  context.fillRect(0, 0, width, height);
  context.drawImage(bitmap, 0, 0, width, height);
  if (bitmap.close) {
    bitmap.close();
  }

  // toBlob uses a callback, so we wrap it in a Promise to use await.
  var blob = await new Promise(function (resolve) {
    canvas.toBlob(resolve, "image/jpeg", 0.8);
  });

  // Only use the new photo if it is really smaller.
  if (!blob || blob.size >= file.size) {
    return null;
  }

  var newName = file.name.replace(/\.[^.]+$/, "") + ".jpg";
  return new File([blob], newName, { type: "image/jpeg" });
}

// Put a File into the file box, as if the person had chosen it themselves.
function putFileInInput(input, file) {
  var transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
}


// ---------------------------------------------------------------------------
// 3. Report form: saved draft (localStorage)
// ---------------------------------------------------------------------------

/*
  Why only these three fields are saved: category, street and description.

  We NEVER save the name or cell number (or the photo), because:
    - localStorage is plain text. It is not encrypted.
    - It stays on the phone until someone deletes it. Many residents share
      a phone, or borrow one, so the next person could read it.
    - Any script running on this site could read it, for example if an XSS
      mistake ever got in. Name and cell number are personal information
      under POPIA, so we keep as little of it as possible.
    - Typing a name and number again takes seconds. Retyping a long
      description is what people actually find annoying.
*/

function saveDraft() {
  try {
    var draft = {
      category: byId("category").value,
      street: byId("street").value,
      description: byId("description").value
    };
    if (draft.category === "" && draft.street === "" && draft.description === "") {
      localStorage.removeItem(DRAFT_KEY); // nothing typed, nothing to keep
    } else {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    }
  } catch (error) {
    // localStorage can be blocked (private browsing) or full. The form still
    // works without a draft, so we just carry on.
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch (error) {
    // nothing to do
  }
}

// Put saved text back, but only into fields that are still empty.
function restoreDraft() {
  var saved = null;
  try {
    saved = JSON.parse(localStorage.getItem(DRAFT_KEY));
  } catch (error) {
    return false; // missing or damaged draft
  }
  if (!saved || typeof saved !== "object") {
    return false;
  }

  var restored = false;
  var category = byId("category");
  var street = byId("street");
  var description = byId("description");

  if (category.value === "" && typeof saved.category === "string" && saved.category !== "") {
    category.value = saved.category; // ignored by the browser if it is not one of the options
    restored = restored || category.value !== "";
  }
  if (street.value === "" && typeof saved.street === "string" && saved.street !== "") {
    street.value = saved.street.slice(0, 150);
    restored = true;
  }
  if (description.value === "" && typeof saved.description === "string" && saved.description !== "") {
    description.value = saved.description.slice(0, 500);
    restored = true;
  }
  return restored;
}

function setupDraft() {
  var message = byId("draft-message");
  var timer = null;
  var announced = false;

  function discardDraft() {
    clearDraft();
    byId("category").value = "";
    byId("street").value = "";
    byId("description").value = "";
    message.textContent = "The saved draft was deleted.";
  }

  // Tell the person that the old typing came back, and let them delete it.
  if (restoreDraft() && message) {
    message.textContent =
      "We brought back what you typed earlier. Your name and cell number are " +
      "not saved, so please type them again. ";
    var button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-link p-0 align-baseline";
    button.textContent = "Delete the saved draft";
    button.addEventListener("click", discardDraft);
    message.appendChild(button);
    announced = true;
  }

  // Save a moment after the person stops typing (not on every key press).
  function scheduleSave() {
    clearTimeout(timer);
    timer = setTimeout(function () {
      saveDraft();
      if (!announced && message) {
        message.textContent =
          "Your typing is saved on this phone in case you lose signal. " +
          "Your name and cell number are never saved.";
        announced = true;
      }
    }, 600);
  }

  ["category", "street", "description"].forEach(function (id) {
    var field = byId(id);
    field.addEventListener("input", scheduleSave);
    field.addEventListener("change", scheduleSave);
  });
}


// ---------------------------------------------------------------------------
// Put the report form together
// ---------------------------------------------------------------------------

function setupReportForm() {
  var form = byId("report-form");
  if (!form) {
    return;
  }

  // Turn off the browser's own error bubbles. We show our own messages next
  // to each field instead, which work better with screen readers.
  form.noValidate = true;

  var fieldIds = Object.keys(fieldRules);
  var photoInput = byId("photo");
  var photoInfo = byId("photo-info");
  var shrinking = null; // holds a Promise while a photo is being shrunk

  // Check a field when the person leaves it. While a field shows an error,
  // check it again on every key press so the message goes away as soon as
  // the problem is fixed.
  fieldIds.forEach(function (id) {
    var field = byId(id);
    field.addEventListener("blur", function () {
      validateField(field);
    });
    field.addEventListener("input", function () {
      if (field.classList.contains("is-invalid")) {
        validateField(field);
      }
    });
    field.addEventListener("change", function () {
      validateField(field);
    });
  });

  // When a photo is chosen: check it, then try to make it smaller.
  photoInput.addEventListener("change", function () {
    if (photoInfo) {
      photoInfo.textContent = "";
    }
    var original = photoInput.files[0];
    if (!original || PHOTO_TYPES.indexOf(original.type) === -1) {
      validatePhoto(photoInput); // shows the "wrong type" message, or clears it
      return;
    }

    shrinking = shrinkPhoto(original)
      .then(function (smaller) {
        if (smaller) {
          putFileInInput(photoInput, smaller);
          if (photoInfo) {
            photoInfo.textContent =
              "Photo made smaller to save your data: " +
              formatSize(original.size) + " down to " + formatSize(smaller.size) + ".";
          }
        }
      })
      .catch(function (error) {
        console.warn("Could not shrink the photo, sending the original.", error);
      })
      .then(function () {
        shrinking = null;
        validatePhoto(photoInput);
      });
  });

  // When the form is sent: check everything. If something is wrong, stop the
  // submit, and move the cursor to the first problem.
  form.addEventListener("submit", function (event) {
    // A photo is still being shrunk: wait for it, then send again.
    if (shrinking) {
      event.preventDefault();
      shrinking.then(function () {
        if (form.requestSubmit) {
          form.requestSubmit();
        } else {
          form.submit();
        }
      });
      return;
    }

    var firstProblem = null;
    fieldIds.forEach(function (id) {
      var field = byId(id);
      if (!validateField(field) && firstProblem === null) {
        firstProblem = field;
      }
    });
    if (!validatePhoto(photoInput) && firstProblem === null) {
      firstProblem = photoInput;
    }

    if (firstProblem !== null) {
      event.preventDefault();
      firstProblem.focus();
    }
  });

  setupDraft();
}


// ---------------------------------------------------------------------------
// After a report is saved: the confirmation page deletes the draft
// ---------------------------------------------------------------------------

function setupConfirmation() {
  if (document.querySelector("[data-clear-draft]")) {
    clearDraft();
  }
}


// ---------------------------------------------------------------------------
// 4. All reports page: live filter
// ---------------------------------------------------------------------------

function setupLiveFilter() {
  var table = byId("reports-table");
  var category = byId("filter-category");
  var status = byId("filter-status");
  var count = byId("filter-count");
  var form = byId("filter-form");
  if (!table || !category || !status) {
    return;
  }

  // Show or hide each row. Nothing is sent to the server.
  function applyFilter() {
    var rows = table.querySelectorAll("tbody tr");
    var shown = 0;

    rows.forEach(function (row) {
      var categoryMatches = category.value === "" || row.dataset.category === category.value;
      var statusMatches = status.value === "" || row.dataset.status === status.value;
      row.hidden = !(categoryMatches && statusMatches);
      if (!row.hidden) {
        shown = shown + 1;
      }
    });

    if (count) {
      if (shown === 0) {
        count.textContent = "No reports match these filters.";
      } else {
        count.textContent =
          "Showing " + shown + " of " + rows.length + " report" + (rows.length === 1 ? "" : "s") + ".";
      }
    }
  }

  category.addEventListener("change", applyFilter);
  status.addEventListener("change", applyFilter);

  // The "Apply filter" button now filters instantly instead of reloading.
  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      applyFilter();
    });
  }

  // The "Clear" link resets both lists. If the page was opened with a filter
  // in its address, some rows were never sent, so we let the link reload.
  var clearLink = byId("filter-clear");
  if (clearLink && window.location.search === "") {
    clearLink.addEventListener("click", function (event) {
      event.preventDefault();
      category.value = "";
      status.value = "";
      applyFilter();
    });
  }

  applyFilter();
}


// ---------------------------------------------------------------------------
// 5. Dashboard: fetch() the JSON counts
// ---------------------------------------------------------------------------

async function refreshCounts(url, message) {
  try {
    var response = await fetch(url, {
      headers: { Accept: "application/json" },
      credentials: "same-origin"
    });

    if (response.status === 401) {
      message.textContent = "Please log in again to refresh the counts.";
      return;
    }
    if (!response.ok) {
      throw new Error("The server answered " + response.status);
    }

    var data = await response.json();

    byId("total-count").textContent = data.total;

    document.querySelectorAll("td[data-category]").forEach(function (cell) {
      var value = data.by_category[cell.dataset.category];
      if (value !== undefined) {
        cell.textContent = value;
      }
    });
    document.querySelectorAll("td[data-status]").forEach(function (cell) {
      var value = data.by_status[cell.dataset.status];
      if (value !== undefined) {
        cell.textContent = value;
      }
    });

    message.textContent = "Counts updated at " + new Date().toLocaleTimeString("en-ZA") + ".";
  } catch (error) {
    // For example: no signal. The numbers on the page stay as they were.
    message.textContent = "Could not refresh the counts. The numbers shown may be out of date.";
  }
}

function setupDashboard() {
  var dashboard = byId("dashboard");
  if (!dashboard) {
    return;
  }
  var url = dashboard.dataset.summaryUrl;
  var message = byId("refresh-message");
  var button = byId("refresh-counts");

  button.addEventListener("click", function () {
    message.textContent = "Refreshing...";
    refreshCounts(url, message);
  });

  refreshCounts(url, message); // also fetch once when the page opens
}


// ---------------------------------------------------------------------------
// 6. Service worker (the PWA's offline support)
// ---------------------------------------------------------------------------

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return;
  }
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function (error) {
      console.warn("The service worker could not be registered.", error);
    });
  });
}


// ---------------------------------------------------------------------------
// Start everything. Each part is wrapped so that if one part has a problem,
// the others still run.
// ---------------------------------------------------------------------------

function safely(setup) {
  try {
    setup();
  } catch (error) {
    console.error("A page script had a problem:", error);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  safely(setupReportForm);
  safely(setupConfirmation);
  safely(setupLiveFilter);
  safely(setupDashboard);
  safely(registerServiceWorker);
});
