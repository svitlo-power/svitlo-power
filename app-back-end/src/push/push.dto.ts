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

const objectIdPattern = /^[0-9a-fA-F]{24}$/;

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
