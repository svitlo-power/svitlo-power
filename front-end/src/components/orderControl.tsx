import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Button, Group } from "@mantine/core";
import { FC } from "react";

type OrderControlProps = {
  order: number;
  maxOrder: number;
  onOrderChange: (currentOrder: number, change: OrderChangeDirection) => void;
  horizontal?: boolean;
};

export enum OrderChangeDirection {
  UP = -1,
  DOWN = 1,
}

export const OrderControl: FC<OrderControlProps> = ({ order, maxOrder, onOrderChange, horizontal }) => {
  return <Group p={0} justify="center">
      <Button.Group>
        <Button 
          disabled={order === 1}
          onClick={() => onOrderChange(order, OrderChangeDirection.UP)}
        >
          <FontAwesomeIcon icon={horizontal ? 'left-long' : 'up-long'}/>
        </Button>
        <Button
          variant="default"
          disabled
          style={{ cursor: 'default' }}
        >
          {order}
        </Button>
        <Button 
          disabled={order === maxOrder}
          onClick={() => onOrderChange(order, OrderChangeDirection.DOWN)}
        >
          <FontAwesomeIcon icon={horizontal ? 'right-long' : 'down-long'}/>
        </Button>
      </Button.Group>
    </Group>;
};