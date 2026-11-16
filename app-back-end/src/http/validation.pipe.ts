import { UnprocessableEntityException, ValidationPipe } from "@nestjs/common";

export function createValidationPipe(): ValidationPipe {
  return new ValidationPipe({
    transform: true,
    whitelist: true,
    exceptionFactory: (errors) =>
      new UnprocessableEntityException({
        detail: errors.map((error) => ({
          loc: ["body", error.property],
          msg: Object.values(error.constraints ?? {}).join(", "),
          type: "value_error",
        })),
      }),
  });
}
