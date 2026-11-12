import { HttpStatus } from "@nestjs/common";
import { NestExpressApplication } from "@nestjs/platform-express";
import type { NextFunction, Request, Response } from "express";

/**
 * JSON body parsing with FastAPI's answer to malformed JSON: 422 with a
 * `json_invalid` detail instead of Express's 400. Create the app with
 * `bodyParser: false` so this parser (and only JSON) is registered.
 */
export function setupBodyParsing(app: NestExpressApplication): void {
  app.useBodyParser("json");
  app.use(
    (error: unknown, _req: Request, res: Response, next: NextFunction) => {
      if (!isJsonParseError(error)) return next(error);
      const position = /position (\d+)/.exec(error.message)?.[1];
      res.status(HttpStatus.UNPROCESSABLE_ENTITY).json({
        detail: [
          {
            type: "json_invalid",
            loc: ["body", position === undefined ? 0 : Number(position)],
            msg: "JSON decode error",
          },
        ],
      });
    },
  );
}

function isJsonParseError(error: unknown): error is SyntaxError {
  return (
    error instanceof SyntaxError &&
    (error as SyntaxError & { type?: string }).type === "entity.parse.failed"
  );
}
