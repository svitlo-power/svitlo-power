import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import { IsArray, IsOptional, IsString, Matches } from "class-validator";

const objectIdPattern = /^[0-9a-fA-F]{24}$/;

export class BuildingIdsDto {
  @ApiProperty({ type: [String], example: ["507f1f77bcf86cd799439011"] })
  @IsArray()
  @Matches(objectIdPattern, { each: true })
  buildingIds!: string[];
}

export class PowerLogsDto {
  @ApiPropertyOptional({ format: "date-time", example: "2026-01-01T00:00:00Z" })
  @IsOptional()
  @IsString()
  startDate?: string;

  @ApiPropertyOptional({ format: "date-time", example: "2026-01-02T00:00:00Z" })
  @IsOptional()
  @IsString()
  endDate?: string;
}
