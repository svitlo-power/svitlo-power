import { Box } from "@mantine/core";
import classes from './styles/statCard.module.css';
import { FC, useRef } from "react";

type SceneryContainerProps = {
  christmasTree: boolean;
  hovered: boolean;
};

export const SceneryContainer: FC<SceneryContainerProps> = ({ christmasTree, hovered }) => {
    const sceneryRef = useRef<
    {
      scale: number;
      x: number;
      opacity: number;
      zIndex: number;
      width: number;
      height: number;
      roof: 'flat' | 'step' | 'peak';
      antenna: boolean;
    }[]
  >([]);

  if (sceneryRef.current.length === 0) {
    const rand = (min: number, max: number) =>
      // eslint-disable-next-line react-hooks/purity
      Math.random() * (max - min) + min;

    const BUILDING_COUNT = 10;

    let x = -40;

    sceneryRef.current = Array.from({ length: BUILDING_COUNT }).map(() => {
      const width = rand(45, 90);

      x += width + rand(8, 25);

      const scale = rand(0.45, 1);
      const height = rand(80, 210);

      return {
        scale,
        x,
        width,
        height,
        opacity: rand(0.18, 0.45),
        zIndex: Math.round(scale * 10),
        roof: ['flat', 'step', 'peak'][Math.floor(rand(0, 3))] as
          | 'flat'
          | 'step'
          | 'peak',
        // eslint-disable-next-line react-hooks/purity
        antenna: Math.random() > 0.75,
      };
    });
  }
  
  return <Box className={classes.sceneryContainer}>
      {christmasTree
        ? sceneryRef.current.map((t, i) => {
            const parallaxX =
              i === 0
                ? 0
                : hovered
                  ? (0.5 - t.scale) * 50
                  : 0;

            const baseY = i === 0 ? 40 : 10;

            return (
              <Box
                key={i}
                className={classes.treeWrapper}
                style={{
                  transform: `
                    translate(${t.x + parallaxX}px, ${baseY}px)
                    scale(${t.scale})
                  `,
                  opacity: t.opacity,
                  zIndex: t.zIndex,
                }}
              >
                <Box className={classes.treeTriangle1} />
                <Box className={classes.treeTriangle2} />
                <Box className={classes.treeTriangle3} />
              </Box>
            );
          })
        : sceneryRef.current.map((b, i) => {
            const parallaxX = hovered ? (0.5 - b.scale) * 40 : 0;

            return (
              <Box
                key={i}
                className={classes.buildingWrapper}
                style={{
                  transform: `
                    translate(${b.x + parallaxX}px, 0)
                    scale(${b.scale})
                  `,
                  opacity: b.opacity,
                  zIndex: b.zIndex,
                }}
              >
                <Box
                  className={`${classes.building} ${
                    b.roof === 'step'
                      ? classes.stepRoof
                      : b.roof === 'peak'
                        ? classes.peakRoof
                        : ''
                  } ${b.antenna ? classes.antenna : ''}`}
                  style={{
                    width: b.width,
                    height: b.height,
                  }}
                />
              </Box>
            );
          })}
    </Box>;
}