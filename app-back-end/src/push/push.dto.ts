import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import {
  IsArray,
  IsBoolean,
  IsIn,
  IsOptional,
  IsString,
  Matches,
  MaxLength,
  MinLength,
} from "class-validator";
import { objectIdPattern } from "../dashboard/dashboard.dto.js";
import { AcceptsAlias } from "../http/aliases.js";

export class DeviceRegistrationDto {
  @ApiProperty({ minLength: 1, maxLength: 4096, writeOnly: true })
  @IsString()
  @MinLength(1)
  @MaxLength(4096)
  token!: string;

  @ApiProperty({ enum: ["android", "ios"] })
  @IsIn(["android", "ios"])
  platform!: "android" | "ios";

  @ApiPropertyOptional({ default: "uk" })
  @IsOptional()
  @IsString()
  language = "uk";

  @ApiPropertyOptional()
  @AcceptsAlias("appVersion", "app_version")
  @IsOptional()
  @IsString()
  appVersion?: string;
}

export class DeviceTokenDto {
  @ApiProperty({ minLength: 1, maxLength: 4096, writeOnly: true })
  @IsString()
  @MinLength(1)
  @MaxLength(4096)
  token!: string;
}

export class DeviceSubscriptionsDto extends DeviceTokenDto {
  @ApiPropertyOptional({ default: true })
  @IsOptional()
  @IsBoolean()
  enabled = true;

  @ApiPropertyOptional({ type: [String], default: [] })
  @AcceptsAlias("disabledTopics", "disabled_topics", () => [])
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  disabledTopics: string[] = [];

  @ApiPropertyOptional({ type: [String], default: [] })
  @IsOptional()
  @IsArray()
  @Matches(objectIdPattern, { each: true })
  buildings: string[] = [];
}
