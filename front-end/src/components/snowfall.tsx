import { useEffect, useState, useCallback } from "react";
import SnowfallEffect from "react-snowfall";
import { isChristmasSeason } from "../utils";

export function Snowfall() {
  const [isActive, setIsActive] = useState(() => isChristmasSeason());
  const [wind, setWind] = useState<[number, number]>([-0.5, 1]);

  useEffect(() => {
    const interval = setInterval(() => {
      setIsActive(isChristmasSeason());
    }, 3600000);

    return () => clearInterval(interval);
  }, []);

  const handleDeviceOrientation = useCallback(
    (event: DeviceOrientationEvent) => {
      const gamma = event.gamma ?? 0;
      const normalizedWind = (gamma / 90) * 3;
      const windMin = Math.max(-3, normalizedWind - 0.5);
      const windMax = Math.min(3, normalizedWind + 0.5);

      setWind([windMin, windMax]);
    },
    []
  );

  useEffect(() => {
    if (!isActive) return;

    if (typeof DeviceOrientationEvent === "undefined") return;

    // iOS 13+ requires permission request
    const requestPermission = async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const DeviceOrientationEventTyped = DeviceOrientationEvent as any;

      if (typeof DeviceOrientationEventTyped.requestPermission === "function") {
        try {
          const permission =
            await DeviceOrientationEventTyped.requestPermission();
          if (permission === "granted") {
            window.addEventListener(
              "deviceorientation",
              handleDeviceOrientation
            );
          }
        } catch {
          // Permission denied or error
        }
      } else {
        window.addEventListener("deviceorientation", handleDeviceOrientation);
      }
    };

    requestPermission();

    return () => {
      window.removeEventListener("deviceorientation", handleDeviceOrientation);
    };
  }, [isActive, handleDeviceOrientation]);

  if (!isActive) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 9999,
      }}
      aria-hidden="true"
    >
      <SnowfallEffect
        snowflakeCount={100}
        wind={wind}
        speed={[0.5, 2]}
        radius={[1, 4]}
        color="#fff"
      />
    </div>
  );
}
