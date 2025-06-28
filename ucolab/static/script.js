      document.addEventListener("mousemove", (e) => {
        const svgContainer = document.querySelector(".svg-container img");
        const { clientX, clientY } = e;
        const { innerWidth, innerHeight } = window;

        const x = (clientX / innerWidth - 0.5) * -2;
        const y = (clientY / innerHeight - 0.8) * -2;

        const moveX = x * 200;
        const moveY = y * 200;

        svgContainer.style.transform = `translate(${moveX}px, ${moveY}px)`;
      });