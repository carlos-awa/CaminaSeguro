// Configuración del mapa
const map = L.map("map").setView([20.523, -100.814], 13);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap",
}).addTo(map);

// Paleta de colores mejorada
const colores = {
  rojo: "#e74c3c", // Rojo más intenso
  amarillo: "#f39c12", // Amarillo oscuro
  verde: "#2ecc71", // Verde brillante
  default: "#95a5a6", // Gris para datos faltantes
};

// Fetch y visualización de datos
fetch("/api/colonias")
  .then((response) => {
    if (!response.ok) throw new Error("Error en la API");
    return response.json();
  })
  .then((data) => {
    if (!data || data.length === 0) {
      console.warn("La API no devolvió datos");
      return;
    }

    // Capa para agrupar círculos (mejor control)
    const markersLayer = L.layerGroup().addTo(map);

    data.forEach((zona) => {
      if (!zona.coordenadas?.coordinates) {
        console.warn("Zona sin coordenadas:", zona.colonia);
        return;
      }

      // Radio dinámico basado en total de incidentes
      const radio = Math.min(15, 5 + Math.sqrt(zona.total));

      // Crea el círculo con estilo mejorado
      L.circleMarker(
        [zona.coordenadas.coordinates[1], zona.coordenadas.coordinates[0]], // [lat, lon]
        {
          radius: radio,
          fillColor: colores[zona.nivel_peligro] || colores.default,
          color: "#34495e",
          weight: 1.5,
          fillOpacity: 0.8,
          className: `peligro-${zona.nivel_peligro}`, // Para estilos CSS personalizados
        }
      )
        .bindPopup(
          `
                <div class="popup-peligro">
                    <h4>${zona.colonia}</h4>
                    <p><strong>Nivel:</strong> <span class="nivel-${
                      zona.nivel_peligro
                    }">${zona.nivel_peligro.toUpperCase()}</span></p>
                    <p><strong>Incidentes:</strong> ${zona.total}</p>
                </div>
            `
        )
        .addTo(markersLayer);
    });

    // Ajusta el zoom para mostrar todos los círculos
    if (data.length > 0) {
      const coords = data
        .filter((d) => d.coordenadas)
        .map((d) => [
          d.coordenadas.coordinates[1],
          d.coordenadas.coordinates[0],
        ]);
      map.fitBounds(coords, { padding: [50, 50] });
    }
  })
  .catch((error) => {
    console.error("Error al cargar datos:", error);
    L.marker([20.523, -100.814]).bindPopup("Error al cargar datos").addTo(map);
  });
