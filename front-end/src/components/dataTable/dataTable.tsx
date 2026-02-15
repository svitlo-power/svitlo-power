import { Fragment, useCallback, useEffect } from "react";
import { ActionsColumnMeta, BooleanColumnMeta, Cell, ColumnDef, ColumnFiltersState, flexRender,
  getCoreRowModel, getFilteredRowModel, getPaginationRowModel, getSortedRowModel,
  Header, PaginationState, SortingState, TableOptions, TypedColumnMeta, useReactTable
} from '@tanstack/react-table'
import { Toolbar } from "./toolbar";
import { Box, Group, Table } from "@mantine/core";
import { HeaderCell } from "./headerCell";
import { ActionsCell, BooleanCell } from "./cell";
import useLocalStorage from "../../hooks/useLocalStorage";
import { ColumnDataType, FilterConfig, PagingConfig, PagingInfo, SortingConfig } from "../../types";
import { FilterCell } from "./filterCell";
import { toLocalDateTime } from "../../utils";
import { Paginator } from "./paginator";
import { SortableHeaderCell } from "./sortableHeaderCell";

export type DataTableColumnDef<T, TValue> = ColumnDef<T, TValue> & {
  meta?: TypedColumnMeta<T, TValue>;
};

export type DataTableProps<T> = {
  data: Array<T>;
  fetchAction: (paging?: PagingConfig, sorting?: SortingConfig, filters?: FilterConfig[]) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: DataTableColumnDef<T, any>[];
  defSort?: SortingState;
  tableKey: string;
  refreshKey?: number;
  hideToolbar?: boolean;
  manualSorting?: boolean;
  manualFiltering?: boolean;
  manualPagination?: boolean;
  usePagination?: boolean;
  useFilters?: boolean;
  useSorting?: boolean;
  pagingInfo?: PagingInfo;
};

export const DataTable = <T,>({
    data,
    fetchAction,
    columns,
    defSort,
    tableKey,
    refreshKey,
    hideToolbar,
    manualSorting,
    manualFiltering,
    manualPagination,
    usePagination,
    useFilters,
    useSorting,
    pagingInfo,
  }: DataTableProps<T>) => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stableFetchAction = useCallback(fetchAction, []);

  const fallbackData: T[] = [];

  const getStorageKey = (type: string): string => `${tableKey}_${type}`;
  const [sorting, setSorting] = useLocalStorage<SortingState>(getStorageKey('sorting'), defSort ?? []);
  const [columnFilters, setColumnFilters] = useLocalStorage<ColumnFiltersState>(getStorageKey('filters'), []);
  const [pagination, setPagination] = useLocalStorage<PaginationState>(getStorageKey('paging'), {
      pageIndex: (pagingInfo?.page ?? 0),
      pageSize: pagingInfo?.pageSize ?? 10,
    });

  const toPagingConfig = (paginationState: PaginationState): PagingConfig => ({
    page: paginationState.pageIndex,
    pageSize: paginationState.pageSize,
  });

  const toSortingConfig = (sortingState: SortingState): SortingConfig | undefined => {
    if (sortingState.length > 0) {
      return {
        column: sortingState[0].id,
        order: sortingState[0].desc ? 'desc' : 'asc',
      };
    }
  };

  const getColumnDataType = useCallback((id: string): ColumnDataType=> {
    const dataType = columns.find(f => f.id === id)?.meta?.dataType;
    return dataType === 'actions' ? ColumnDataType.Text : dataType ?? ColumnDataType.Text;
  }, [columns]);

  const toFilteringConfig = useCallback((filters: ColumnFiltersState): FilterConfig[] => {
    const result: FilterConfig[] = [];
    filters?.forEach(f => result.push({
      column: f.id,
      value: f.value,
      dataType: getColumnDataType(f.id),
    }));
    return result;
  }, [getColumnDataType]);

  const fetch = useCallback(() => {
    stableFetchAction(
      toPagingConfig(pagination),
      toSortingConfig(sorting),
      toFilteringConfig(columnFilters),
    );
  }, [stableFetchAction, pagination, sorting, toFilteringConfig, columnFilters]);

  useEffect(() => {
    fetch();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    pagination.pageIndex,
    pagination.pageSize,
    sorting,
    columnFilters,
    refreshKey,
  ]);

  const tableOptions: TableOptions<T> = {
    data: data ?? fallbackData,
    columns: columns,
    state: { sorting, columnFilters, pagination },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualSorting: manualSorting ?? false,
    getFilteredRowModel: getFilteredRowModel(),
    manualFiltering: manualFiltering ?? false,
    getPaginationRowModel: getPaginationRowModel(),
    manualPagination: manualPagination ?? false,
    rowCount: pagingInfo?.total,
  };

  const table = useReactTable<T>(tableOptions);

  const getSortingConfig = (header: Header<T, unknown>): 'ascending' | 'descending' | undefined => {
    return header.column.getIsSorted() 
      ? (header.column.getIsSorted() === "asc" ? "ascending" : "descending")
      : undefined;
  };

  const toggleSorting = (header: Header<T, unknown>): void => {
    if (header.column.columnDef.enableSorting) {
      header.column.toggleSorting(header.column.getIsSorted() === "asc");
    }
  };

  const getCellTextAlign = <T,>(cell: Cell<T, unknown>): 'center' | 'left' | 'right' => {
    return cell.column.columnDef.meta?.textAlign ?? 'left';
  };

  const renderCell = <T,>(cell: Cell<T, unknown>, row: T): React.ReactNode => {
    const columnDef = cell.column.columnDef;
    if (columnDef.meta?.dataType === 'actions') {
      const meta = columnDef.meta as ActionsColumnMeta<T, unknown>;
      return <ActionsCell<T>
        actions={meta.actions ?? []}
        row={row}
      />;
    } else if (columnDef.meta?.dataType === ColumnDataType.Boolean) {
      const meta = columnDef.meta as BooleanColumnMeta<T, unknown>;
      if (meta.customRender) {
        return flexRender(columnDef.cell, cell.getContext());
      }
      return <Group p={0} justify="center">
        <BooleanCell
          value={cell.getValue() as boolean}
          readonly={meta.readOnly}
          row={row}
          checkedChange={meta.checkedChange}
        />
      </Group>;
    } else if (columnDef.meta?.dataType === ColumnDataType.DateTime) {
      const value = cell.getValue();
      return toLocalDateTime(value as string | Date) || '-';
    }
    return flexRender(columnDef.cell, cell.getContext());
  };

  return <Box pt="sm">
    { !hideToolbar && <Toolbar
        usePagination={usePagination ?? false}
        pageSize={pagingInfo?.pageSize ?? 10}
        onPageSizeChange={v => setPagination({
          ...pagination,
          pageSize: v
        })}
        totalRecords={usePagination && pagingInfo ? pagingInfo.total : data?.length ?? 0 }
        refresh={() => fetch()}
      /> }
    <Table.ScrollContainer minWidth={'100%'}>
      <Table striped key={`${tableKey}_table`} highlightOnHover withColumnBorders>
        <Table.Thead>
          {table.getHeaderGroups().map(headerGroup => (
            <Fragment key={headerGroup.id}>
              <Table.Tr key={`${headerGroup.id}_main`}>
                {headerGroup.headers.map(header => (
                    (useSorting ?? true)
                      ? <SortableHeaderCell<T>
                          sorting={getSortingConfig(header)}
                          toggleSorting={() => toggleSorting(header)}
                          header={header}
                          key={header.id}
                        />
                      : <HeaderCell<T>
                          header={header}
                          key={header.id}
                        />
                    ))}
              </Table.Tr>
              { useFilters && <Table.Tr key={`${headerGroup.id}_fltg`}>
                {headerGroup.headers.map(header => {
                  const enableFilter = header.column.columnDef.enableColumnFilter;
                  return <Table.Th key={`${header.id}_flt`}>
                    {enableFilter && <FilterCell<T> header={header} /> }
                  </Table.Th>
                })}
              </Table.Tr> }
            </Fragment>
          ))}
        </Table.Thead>
        <Table.Tbody>
          {table.getRowModel().rows.map(row => (
            <Table.Tr key={row.id}>
              {row.getVisibleCells().map(cell => (
                <Table.Td
                  key={cell.id}
                  ta={getCellTextAlign(cell)}
                >
                  {renderCell(cell, row.original)}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
    { usePagination && <Paginator<T> table={table} recordsCount={pagingInfo?.total ?? 0} /> }
  </Box>
}
