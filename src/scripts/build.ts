import fs from 'fs-extra';
import path from 'path';

// Clean the destination directory while preserving items on the ignore list
async function cleanDirectory(directory: string, ignoreList: string[]): Promise<void> {
    const items = await fs.readdir(directory, { withFileTypes: true });

    for (const item of items) {
        const fullPath = path.join(directory, item.name);
        const relativePath = path.relative(directory, fullPath);

        if (ignoreList.some(ignored => relativePath.startsWith(ignored))) {
            continue;
        }

        try {
            if (item.isDirectory()) {
                await cleanDirectory(fullPath, ignoreList); // Recursively clean subdirectories
            }

            await fs.remove(fullPath);
        } catch (err) {
            console.error(`Error removing ${fullPath}:`, err);
        }
    }
}

// Copy files from src to dest relative to the given destDir
async function copyFiles(fileMappings: { item: string, src: string; dest: string }[], destDir: string): Promise<void> {
    for (const { item, src, dest } of fileMappings) {
        const destPath = path.join(destDir, dest);

        // Check if the source file exists
        try {
            await fs.access(src);
        } catch {
            console.error(`Source file not found: ${src}`);
            continue;
        }

        try {
            await fs.copy(src, destPath);
            console.log(`Successfully copied ${item} to destination`)
        } catch (err) {
            console.error(`Error copying ${src} to ${destPath}:`, err);
        }
    }
}

// Main function to coordinate cleaning and copying
async function main(destDir: string, ignoreList: string[], filesToCopy: { item: string, src: string; dest: string }[]): Promise<void> {
    try {
        // Ensure destDir exists
        await fs.ensureDir(destDir);

        // Clean the destination directory
        await cleanDirectory(destDir, ignoreList);

        // Copy files to the destination directory
        await copyFiles(filesToCopy, destDir);

        console.log('Build process completed successfully');
    } catch (err) {
        console.error('Error during build process:', err);
    }
}

// Example usage
const destDir = path.resolve('../web'); // Ensure the path is absolute
const ignoreList = ['.gitkeep', 'preserve-this-folder/'];
const filesToCopy = [
    { item: 'HTMX JS Library files', src: path.resolve('./node_modules/htmx.org/dist/htmx.min.js'), dest: 'static/htmx.min.js' },
    { item: 'flowbite UI files', src: path.resolve('./node_modules/flowbite/dist/flowbite.min.js'), dest: 'static/flowbite.min.js' },
    { item: 'asset files', src: path.resolve('./assets'), dest: 'assets' },
    { item: 'templates directory', src: path.resolve('./templates'), dest: 'templates' }
];

main(destDir, ignoreList, filesToCopy);
