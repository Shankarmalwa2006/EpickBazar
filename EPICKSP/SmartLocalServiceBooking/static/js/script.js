// Basic, beginner-friendly form validation for a better UX.
// Works alongside Bootstrap validation styles.

function todayISO() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function trimValue(el) {
  if (!el) return "";
  return (el.value || "").trim();
}

function setDateMinForBookingForms() {
  const dateInputs = document.querySelectorAll('form[data-validate="booking"] input[type="date"][name="booking_date"]');
  const min = todayISO();
  dateInputs.forEach((input) => {
    input.setAttribute("min", min);
  });
}

function attachConfirmHandlers() {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    });
  });
}

function runExtraValidation(form) {
  const kind = form.getAttribute("data-validate");

  if (kind === "register") {
    const name = form.querySelector('input[name="name"]');
    const password = form.querySelector('input[name="password"]');
    if (name) name.value = trimValue(name);
    if (password && trimValue(password).length < 6) {
      password.setCustomValidity("Password must be at least 6 characters.");
    } else if (password) {
      password.setCustomValidity("");
    }
  }

  if (kind === "login") {
    const email = form.querySelector('input[name="email"]');
    if (email) email.value = trimValue(email);
  }

  if (kind === "service") {
    const price = form.querySelector('input[name="price"]');
    if (price) {
      const v = Number(price.value);
      if (Number.isNaN(v) || v < 0) {
        price.setCustomValidity("Price must be a non-negative number.");
      } else {
        price.setCustomValidity("");
      }
    }
  }

  if (kind === "booking") {
    const date = form.querySelector('input[name="booking_date"]');
    const addr = form.querySelector('textarea[name="address"]');

    if (addr) {
      addr.value = trimValue(addr);
      if (addr.value.length < 10) {
        addr.setCustomValidity("Please enter a more complete address.");
      } else {
        addr.setCustomValidity("");
      }
    }

    if (date) {
      const min = date.getAttribute("min") || todayISO();
      if (date.value && date.value < min) {
        date.setCustomValidity("Booking date cannot be in the past.");
      } else {
        date.setCustomValidity("");
      }
    }
  }
}

function attachBootstrapValidation() {
  const forms = document.querySelectorAll(".needs-validation");

  Array.from(forms).forEach((form) => {
    form.addEventListener(
      "submit",
      (event) => {
        runExtraValidation(form);

        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }

        form.classList.add("was-validated");
      },
      false
    );
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setDateMinForBookingForms();
  attachConfirmHandlers();
  attachBootstrapValidation();
});

