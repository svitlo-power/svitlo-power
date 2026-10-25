if (process.env.CI || process.env.NODE_ENV === "production") {
  process.exit(0);
}

const { default: husky } = await import("husky");
husky();
