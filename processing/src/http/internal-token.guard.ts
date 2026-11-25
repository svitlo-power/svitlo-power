import {
  CanActivate,
  ExecutionContext,
  Inject,
  Injectable,
  UnauthorizedException,
} from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { timingSafeEqual } from "node:crypto";
import { Request } from "express";
import { processingConfig } from "../config/processing.config.js";

/**
 * Paths that must stay reachable without a token.
 *
 * Liveness and readiness are container probes and cannot send credentials; the
 * metrics port is a separate listener and never passes through this guard.
 */
const PUBLIC_PATHS = new Set(["/health/live", "/health/ready"]);

/**
 * Authenticates internal callers with the shared `INTERNAL_API_TOKEN`.
 *
 * The refresh trigger makes Processing rebuild and publish a snapshot, so it is
 * a write side effect even in shadow mode. It must not be callable by anything
 * that merely shares the Docker network.
 */
@Injectable()
export class InternalTokenGuard implements CanActivate {
  constructor(
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
  ) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    if (PUBLIC_PATHS.has(request.path)) return true;

    const expected = this.config.internalApiToken;
    // Refuse rather than silently allowing unauthenticated writes when the
    // deployment has not configured a token.
    if (!expected) {
      throw new UnauthorizedException("Internal API token is not configured");
    }

    const supplied = request.header("Authorization");
    if (!supplied?.startsWith("Bearer ")) {
      throw new UnauthorizedException("Invalid internal API token");
    }

    const expectedBytes = Buffer.from(expected);
    const suppliedBytes = Buffer.from(supplied.slice("Bearer ".length));
    if (
      expectedBytes.length !== suppliedBytes.length ||
      !timingSafeEqual(expectedBytes, suppliedBytes)
    ) {
      throw new UnauthorizedException("Invalid internal API token");
    }
    return true;
  }
}
