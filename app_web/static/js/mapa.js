// Inicializar mapa centrado en Celaya
const map = L.map("map").setView([20.523, -100.814], 13);

// Añadir capa base (OpenStreetMap)
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

// Colores según nivel de peligro
const colores = {
  rojo: "#ff0000",
  amarillo: "#ffff00",
  verde: "#00ff00",
};

// Obtener datos de la API
fetch("/api/zonas")
  .then((response) => response.json())
  .then((data) => {
    console.log("Datos recibidos:", data); // Verifica en consola

    data.forEach((zona) => {
      if (!zona.coords?.coordinates) {
        console.warn("Zona sin coordenadas válidas:", zona);
        return;
      }

      const color =
        {
          rojo: "#ff0000",
          amarillo: "#ffcc00",
          verde: "#00aa00",
        }[zona.nivel] || "#999";

      L.circleMarker(
        [zona.coords.coordinates[1], zona.coords.coordinates[0]], // [lat, lon]
        {
          radius: 8 + zona.total * 0.5, // Radio proporcional a incidentes
          fillColor: color,
          color: "#333",
          weight: 1,
          fillOpacity: 0.8,
        }
      )
        .bindPopup(
          `
                <b>${zona.colonia}</b><br>
                Total incidentes: ${zona.total}<br>
                Nivel: ${zona.nivel.toUpperCase()}
            `
        )
        .addTo(map);
    });
  })
  .catch((error) => console.error("Error:", error));
