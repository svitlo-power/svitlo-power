import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from "@nestjs/common";
import { Request, Response } from "express";
import { InternalApiError } from "../shared.js";

const PASSTHROUGH_UPSTREAM_STATUSES = new Set([400, 404, 422, 503, 504]);

/** Renders every error in the FastAPI `{ detail }` shape the mobile app expects. */
@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(ApiExceptionFilter.name);

  catch(error: unknown, host: ArgumentsHost): void {
    const http = host.switchToHttp();
    const request = http.getRequest<Request>();
    const response = http.getResponse<Response>();
    const route = `${request.method} ${request.path}`;
    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let detail: unknown = "Internal server error";

    if (error instanceof InternalApiError) {
      status = PASSTHROUGH_UPSTREAM_STATUSES.has(error.status)
        ? error.status
        : HttpStatus.BAD_GATEWAY;
      detail =
        error.detail ??
        (error.status === 504
          ? "Dependency timed out"
          : "Dependency unavailable");
      if (status >= 500) {
        this.logger.warn(
          `${route} failed: ${error.message} (responded ${status})`,
        );
      }
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
      if (
        status === HttpStatus.NOT_FOUND &&
        typeof detail === "string" &&
        detail.startsWith(`Cannot ${request.method} `)
      ) {
        // Unknown route: match FastAPI's generic text instead of Nest's "Cannot GET /x".
        detail = "Not Found";
      }
    } else {
      this.logger.error(
        `${route} failed with an unhandled error`,
        error instanceof Error ? error.stack : String(error),
      );
    }
    response.status(status).json({ detail });
  }
}
