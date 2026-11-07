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
import { appConfig } from "../config/app.config.js";

@Injectable()
export class AppTokenGuard implements CanActivate {
  constructor(
    @Inject(appConfig.KEY)
    private readonly config: ConfigType<typeof appConfig>,
  ) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    if (
      request.path === "/metrics" ||
      request.path === "/health" ||
      request.path.startsWith("/health/")
    ) {
      return true;
    }
    const expected = this.config.appAccessToken;
    if (!expected) return true;
    const supplied = request.header("X-App-Token");
    if (!supplied) throw new UnauthorizedException("Invalid app token");
    const expectedBytes = Buffer.from(expected);
    const suppliedBytes = Buffer.from(supplied);
    if (
      expectedBytes.length !== suppliedBytes.length ||
      !timingSafeEqual(expectedBytes, suppliedBytes)
    ) {
      throw new UnauthorizedException("Invalid app token");
    }
    return true;
  }
}
