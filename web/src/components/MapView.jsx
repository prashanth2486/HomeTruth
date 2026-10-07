import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

function colorFor(value, min, max) {
  if (max <= min) return "#9c4221";
  const t = Math.min(1, Math.max(0, (value - min) / (max - min)));
  const hue = 28 - t * 18;
  const light = 42 - t * 10;
  return `hsl(${hue} ${58 + t * 12}% ${light}%)`;
}

export default function MapView({ localities, onSelect }) {
  const node = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);

  useEffect(() => {
    if (!node.current || mapRef.current) return undefined;
    const map = L.map(node.current, { scrollWheelZoom: false }).setView([12.97, 77.59], 11);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 18,
    }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    const priced = localities.filter((item) => item.lat != null && item.lon != null);
    if (!priced.length) return;
    const values = priced.map((item) => item.median_asking_inr);
    const min = Math.min(...values);
    const max = Math.max(...values);
    priced.forEach((item) => {
      const radius = 7 + Math.min(item.count, 80) / 8;
      const marker = L.circleMarker([item.lat, item.lon], {
        radius,
        color: "#1c1612",
        weight: 1,
        fillColor: colorFor(item.median_asking_inr, min, max),
        fillOpacity: 0.88,
      });
      marker.bindTooltip(`${item.name}<br>${item.count} asks`);
      marker.on("click", () => onSelect(item));
      marker.addTo(layer);
    });
  }, [localities, onSelect]);

  return <div className="map" ref={node} />;
}
