import { Navigate, RouteObject, RouterProvider, createBrowserRouter } from "react-router-dom";
import { ProtectedRoute } from "./protectedRoute";
import {
  LoginPage, HomePage, StationsPage, StationDetailsPage, BotsPage,
  ChatsPage, MessagesPage, MessageEditPage, UsersPage,
  BuildingsPage, ExtDataPage, NotFoundPage,
  ChangePasswordPage, AppLandingPage, ExtDevicesPage
} from "../pages";
import { FC } from "react";
import { useAppSelector } from "../stores/store";
import { IconName } from "@fortawesome/fontawesome-svg-core";
import { AnonymousLayout } from "../layouts/anonymousLayout";
import { PublicLayout } from "../layouts/publicLayout";
import { authDataSelector } from "../stores/selectors";

export type MenuItem = RouteObject & {
  children?: MenuItem[];
  name?: string;
  icon?: IconName;
  skipForMenu?: boolean;
}

// eslint-disable-next-line react-refresh/only-export-components
export const RootRoutes: MenuItem[] = [
  {
    path: "/",
    name: "routes.home",
    icon: "home",
    Component: HomePage,
  },
  {
    path: "/bots",
    name: "routes.bots",
    icon: "robot",
    Component: BotsPage,
  },
  {
    path: "/stations",
    name: "routes.stations",
    icon: "tower-broadcast",
    Component: StationsPage,
  },
  {
    path: "/stations/details/:stationId",
    name: "routes.stationDetails",
    Component: StationDetailsPage,
    skipForMenu: true,
  },
  {
    path: "/messages",
    name: "routes.messages",
    icon: "envelope",
    Component: MessagesPage,
  },
  {
    path: "/messages/edit/:messageId",
    name: "routes.editMessage",
    element: <MessageEditPage isEdit={true} />,
    skipForMenu: true,
  },
  {
    path: "/messages/create",
    name: "routes.createMessage",
    element: <MessageEditPage isEdit={false} />,
    skipForMenu: true,
  },
  {
    path: "/chats",
    name: "routes.chats",
    icon: "comments",
    Component: ChatsPage,
  },
  {
    path: "/ext-data",
    name: "routes.externalLogs",
    icon: "file-lines",
    Component: ExtDataPage,
  },
  {
    path: "/users",
    name: "routes.users",
    icon: "user-md",
    Component: UsersPage,
  },
  {
    path: '/buildings',
    name: "routes.buildings",
    icon: "building",
    Component: BuildingsPage,
  },
  {
    path: '/ext-devices',
    name: "routes.devices",
    icon: "microchip",
    Component: ExtDevicesPage,
  },
  {
    path: "*",
    name: "routes.notFound",
    Component: NotFoundPage,
    skipForMenu: true,
  },
];

const Routes: FC = () => {
  const authData = useAppSelector(authDataSelector);

  const changePasswordRoute = {
    path: "/changePassword",
    element: (<AnonymousLayout caption="routes.changePassword">
      <ChangePasswordPage />
    </AnonymousLayout>),
  } as RouteObject;

  const loginRoute = {
    path: "/login",
    element: (<AnonymousLayout caption="routes.logIn">
      <LoginPage />
    </AnonymousLayout>),
  } as RouteObject;

  const routesForAuthenticatedOnly: RouteObject[] = [
    changePasswordRoute,
    loginRoute,
    {
      path: "/app",
      element: <AppLandingPage />,
    },
    {
      path: "/",
      element: (<ProtectedRoute />),
      children: RootRoutes,
    },
  ];

  const routesForNotAuthenticated: RouteObject[] = [
    changePasswordRoute,
    loginRoute,
    {
      path: "/app",
      element: <AppLandingPage />,
    },
    {
      path: "/",
      element: <PublicLayout>
        <BuildingsPage />
      </PublicLayout>,
    },
    {
      path: '*',
      element: <Navigate to={"/"} />
    },
  ];

  const router = createBrowserRouter(
    authData?.accessToken ? routesForAuthenticatedOnly : routesForNotAuthenticated
  );

  return <RouterProvider key={authData?.accessToken ? 'authenticated' : 'anonymous'} router={router} />;
};

export default Routes;
