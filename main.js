document.addEventListener("DOMContentLoaded", () => {
  // Select all add-to-cart forms
  const addForms = document.querySelectorAll(".add-row");

  addForms.forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const pid = form.action.split("/").pop(); // get product id from URL
      const qty = formData.get("qty") || 1;

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) throw new Error("Network response was not ok");

        const data = await response.json();

        if (data.success) {
          // Update cart count dynamically
          const cartCount = document.querySelector(".cart-count");
          if (cartCount) {
            cartCount.textContent = data.cart_count;
          } else {
            // If cart-count span doesn't exist yet, create it
            const cartLink = document.querySelector(".nav-right .cta");
            const span = document.createElement("span");
            span.className = "cart-count";
            span.textContent = data.cart_count;
            cartLink.appendChild(span);
          }

          alert(`${data.product_name} added to cart!`);
        } else {
          alert(data.message || "Failed to add item.");
        }
      } catch (err) {
        console.error(err);
        alert("Error adding item to cart.");
      }
    });
  });
});
