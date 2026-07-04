import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Button, Group, useMantineColorScheme } from "@mantine/core";
import { FC } from "react";

type OrderControlProps = {
  order: number;
  maxOrder: number;
  onOrderChange: (currentOrder: number, change: OrderChangeDirection) => void;
  horizontal?: boolean;
};

// eslint-disable-next-line react-refresh/only-export-components
export enum OrderChangeDirection {
  UP = -1,
  DOWN = 1,
}

export const OrderControl: FC<OrderControlProps> = ({ order, maxOrder, onOrderChange, horizontal }) => {
  const { colorScheme } = useMantineColorScheme();

  return <Group p={0} justify="center">
      <Button.Group h={28}>
        <Button
          size="xs"
          h={28}
          disabled={order === 1}
          onClick={() => onOrderChange(order, OrderChangeDirection.UP)}
        >
          <FontAwesomeIcon icon={horizontal ? 'left-long' : 'up-long'}/>
        </Button>
        <Button
          variant="default"
          disabled
          style={{ cursor: 'default' }}
          size="xs"
          h={28}
          bg={colorScheme === 'dark' ? 'dark.2' : 'gray.8'}
        >
          {order}
        </Button>
        <Button 
          size="xs"
          h={28}
          disabled={order === maxOrder}
          onClick={() => onOrderChange(order, OrderChangeDirection.DOWN)}
        >
          <FontAwesomeIcon icon={horizontal ? 'right-long' : 'down-long'}/>
        </Button>
      </Button.Group>
    </Group>;
};