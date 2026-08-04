import { Container, Title, Text, Button, Group, Stack, Card, Grid, Box, SimpleGrid, Image, useMantineColorScheme, Divider, Anchor } from '@mantine/core';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { IconName } from '@fortawesome/fontawesome-svg-core';
import { useState, useEffect } from 'react';
import { ThemePicker } from '../../components';
import { Authors } from '../../layouts/components/authors';
import { VisitTracker } from '../../layouts/components/visitTracker';
import classes from './appLanding.module.css';
import iconDark from '../../assets/icon_dark_with_text.png';
import iconLight from '../../assets/icon_light_with_text.png';
import appImage1 from '../../assets/app/app01.png';
import appImage2 from '../../assets/app/app02.png';
import appImage3 from '../../assets/app/app03.png';
import { initGA, trackPageView } from '../../utils/analytics';

interface FeatureCardProps {
  icon: IconName;
  title: string;
  description: string;
}

const FeatureCard = ({ icon, title, description }: FeatureCardProps) => (
  <Card shadow="sm" padding="lg" radius="md" withBorder>
    <Stack gap="md" align="center">
      <Box className={classes.iconWrapper}>
        <FontAwesomeIcon icon={icon} size="2x" />
      </Box>
      <Title order={4} ta="center">{title}</Title>
      <Text size="sm" c="dimmed" ta="center">
        {description}
      </Text>
    </Stack>
  </Card>
);

export const AppLandingPage = () => {
  const { colorScheme } = useMantineColorScheme();
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState<string>('');
  const [appVersion, setAppVersion] = useState<string>('');
  
  const iconSrc = colorScheme === 'dark' ? iconLight : iconDark;
  const appImages = [appImage1, appImage2, appImage3];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prevIndex) => (prevIndex + 1) % appImages.length);
    }, 3000); 

    return () => clearInterval(interval);
  }, [appImages.length]);

  useEffect(() => {
    const fetchDownloadUrl = async () => {
      try {
        const response = await fetch('/api/app/info');
        const data = await response.json();
        
        if (data.updateUrl) {
          setDownloadUrl(data.updateUrl);
        }
        if (data.version) {
          setAppVersion(data.version);
        }
      } catch (error) {
        console.error('Failed to fetch download URL:', error);
      }
    };

    fetchDownloadUrl();
  }, []);

  // Google Analytics
  useEffect(() => {
    initGA();
    trackPageView('/app', 'App Landing Page');
  }, []);

  const features = [
    {
      icon: 'bolt' as IconName,
      title: 'Real-Time Monitoring',
      description: 'Track the power status of Sviltopark residential complex in real-time from anywhere'
    },
    {
      icon: 'chart-bar' as IconName,
      title: 'Power Statistics',
      description: 'Detailed statistics of power generation and energy usage analytics'
    },
    {
      icon: 'calendar-check' as IconName,
      title: 'Outage Schedule',
      description: 'Stay informed with up-to-date planned power outage schedules for your area'
    },
    {
      icon: 'mobile' as IconName,
      title: 'Modern Interface',
      description: 'Intuitive and beautiful design with dark and light themes for the best user experience'
    }
  ];

  const handleDownload = () => {
    if (downloadUrl) {
      window.open(downloadUrl, '_blank');
    } else {
      console.error('Download URL not available');
    }
  };

  return (
    <Container size="xl">
      <Stack gap="xl" py="xl">
        {/* Header with Theme Switcher */}
        <Group justify="space-between" align="center">
          <Anchor href="/" underline="never">
            <Button variant="subtle" leftSection={<FontAwesomeIcon icon="home" />}>
              Go to Main Page
            </Button>
          </Anchor>
          <ThemePicker isNavbarCollapsed={false} size="md" />
        </Group>

        {/* Hero Section */}
        <Grid gutter="xl">
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Stack gap="lg">
              <Image 
                h={60} 
                w="auto" 
                src={iconSrc} 
                alt="Svitlo Power Logo"
                fit="contain"
                style={{ alignSelf: 'flex-start' }}
              />
              <Title order={2} c="dimmed" fw={500}>
                Complete Power Monitoring for Sviltopark Residential Complex
              </Title>
              <Text size="lg">
                Modern mobile app for monitoring power stations and tracking power outage schedules 
                in Sviltopark. Stay informed about power status and plan your electricity usage 
                with real-time outage updates and schedules.
              </Text>
              <Group>
                <Button 
                  size="lg" 
                  leftSection={<FontAwesomeIcon icon="download" />}
                  onClick={handleDownload}
                  disabled={!downloadUrl}
                >
                  Download APK
                </Button>
              </Group>
              <Group gap="md">
                <Text size="sm" c="dimmed">
                  <FontAwesomeIcon icon="mobile" /> Android 13.0 or higher required
                </Text>
                {appVersion && (
                  <>
                    <Text size="sm" c="dimmed">•</Text>
                    <Text size="sm" c="dimmed">
                      Version {appVersion}
                    </Text>
                  </>
                )}
              </Group>
            </Stack>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Box className={classes.heroImageWrapper}>
              <Box className={classes.phonePreview}>
                {appImages.map((image, index) => (
                  <img
                    key={index}
                    src={image}
                    alt={`Svitlo Power App Screenshot ${index + 1}`}
                    className={`${classes.appScreenshot} ${
                      index === currentImageIndex ? classes.active : ''
                    }`}
                  />
                ))}
              </Box>
              <Box className={classes.carouselDots}>
                {appImages.map((_, index) => (
                  <button
                    key={index}
                    className={`${classes.dot} ${
                      index === currentImageIndex ? classes.activeDot : ''
                    }`}
                    onClick={() => setCurrentImageIndex(index)}
                    aria-label={`Go to screenshot ${index + 1}`}
                  />
                ))}
              </Box>
            </Box>
          </Grid.Col>
        </Grid>

        {/* Features Section */}
        <Box mt="xl">
          <Stack gap="md" mb="xl">
            <Title order={2} ta="center">
              App Features
            </Title>
            <Text size="lg" c="dimmed" ta="center">
              Svitlo Power provides all the essential tools for effective monitoring 
              of power status and tracking outage schedules in Sviltopark
            </Text>
          </Stack>
          
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg">
            {features.map((feature, index) => (
              <FeatureCard key={index} {...feature} />
            ))}
          </SimpleGrid>
        </Box>

        {/* CTA Section */}
        <Card shadow="sm" padding="xl" radius="md" withBorder mt="xl">
          <Stack gap="md" align="center">
            <Title order={3} ta="center">
              Ready to Get Started?
            </Title>
            <Text size="md" ta="center" c="dimmed">
              Download Svitlo Power now and stay informed about power status, 
              outage schedules, and electricity monitoring in Sviltopark residential complex
            </Text>
            <Button 
              size="lg" 
              leftSection={<FontAwesomeIcon icon="download" />}
              onClick={handleDownload}
              disabled={!downloadUrl}
            >
              Download APK
            </Button>
          </Stack>
        </Card>

        {/* Footer */}
        <Divider my="lg" />
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" mb="md">
          <Box ta={{ base: 'center', md: 'left' }}>
            <Authors />
          </Box>
          <Box ta={{ base: 'center', md: 'right' }}>
            <VisitTracker />
          </Box>
        </SimpleGrid>
      </Stack>
    </Container>
  );
};

