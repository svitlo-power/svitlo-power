import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import { IsArray, IsOptional, IsString, Matches } from "class-validator";
import { AcceptsAlias } from "../http/aliases.js";

export const objectIdPattern = /^[0-9a-fA-F]{24}$/;

export class BuildingIdsDto {
  @ApiProperty({ type: [String], example: ["507f1f77bcf86cd799439011"] })
  @AcceptsAlias("buildingIds", "building_ids")
  @IsArray()
  @Matches(objectIdPattern, { each: true })
  buildingIds!: string[];
}

export class PowerLogsDto {
  @ApiPropertyOptional({ format: "date-time", example: "2026-01-01T00:00:00Z" })
  @AcceptsAlias("startDate", "start_date")
  @IsOptional()
  @IsString()
  startDate?: string;

  @ApiPropertyOptional({ format: "date-time", example: "2026-01-02T00:00:00Z" })
  @AcceptsAlias("endDate", "end_date")
  @IsOptional()
  @IsString()
  endDate?: string;
}
