import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
} from "@nestjs/common";
import { Response } from "express";
import { InternalApiError } from "../../../shared/typescript/src/index.js";

@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  catch(error: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();
    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let detail: unknown = "Internal server error";

    if (error instanceof InternalApiError) {
      status = [400, 404, 422, 503, 504].includes(error.status)
        ? error.status
        : 502;
      detail =
        error.detail ??
        (error.status === 504
          ? "Dependency timed out"
          : "Dependency unavailable");
    } else if (error instanceof HttpException) {
      status = error.getStatus();
      const body = error.getResponse();
      if (body && typeof body === "object" && "detail" in body) {
        detail = (body as { detail: unknown }).detail;
      } else if (body && typeof body === "object" && "message" in body) {
        detail = (body as { message: unknown }).message;
      } else {
        detail = body;
      }
    }
    response.status(status).json({ detail });
  }
}
